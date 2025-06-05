import asyncio
from pathlib import Path

import rich
import structlog
from asynciolimiter import Limiter
from google import genai
from google.genai import types

from lmnop_wakeup.audio.config import TTSConfig
from lmnop_wakeup.audio.file_manager import AudioFileManager
from lmnop_wakeup.audio.master import master_briefing_audio
from lmnop_wakeup.audio.speech_config import SpeechConfigBuilder
from lmnop_wakeup.brief.model import BriefingScript, ScriptLine
from lmnop_wakeup.core.logging import rich_sprint
from lmnop_wakeup.core.typing import ensure
from lmnop_wakeup.env import get_litellm_api_key, get_litellm_base_url

logger = structlog.get_logger(__name__)


class TTSProcessor:
  def __init__(self, config: TTSConfig | None = None):
    self.config = config or TTSConfig()
    self.client = genai.Client(
      api_key=get_litellm_api_key(),
      http_options={"base_url": get_litellm_base_url()},
    )
    self.speech_config_builder = SpeechConfigBuilder()
    self.file_manager = AudioFileManager(
      channels=self.config.audio_channels,
      rate=self.config.audio_rate,
      sample_width=self.config.audio_sample_width,
    )

  async def process_script_line(
    self,
    line: ScriptLine,
    part: int,
    output_path: Path,
    rate_limiter: Limiter,
  ) -> None:
    """Process a single script line into audio."""
    speech_config = self.speech_config_builder.build_config({line.character_slug})

    await rate_limiter.wait()

    logger.info(f"Processing TTS for part {part} with speaker {line.character_slug}")

    response = await self.client.aio.models.generate_content(
      model=self.config.model_name,
      contents=line.build_prompt(),
      config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=speech_config,
        temperature=self.config.temperature,
        top_p=self.config.top_p,
      ),
    )

    rich.print(response.usage_metadata)

    # Extract audio data
    candidates = ensure(response.candidates)
    content = ensure(candidates[0].content)
    parts = ensure(content.parts)
    inline_data = ensure(parts[0].inline_data)
    audio_data = ensure(inline_data.data)

    # Save to file
    output_file = output_path / f"{part}.wav"
    self.file_manager.create_wave_file(output_file, audio_data)


class TTSOrchestrator:
  def __init__(self, config: TTSConfig | None = None):
    self.config = config or TTSConfig()
    self.processor = TTSProcessor(self.config)

  async def generate_voiceover(
    self, script: BriefingScript, output_path: Path, print_script: bool = False
  ) -> None:
    """Generate voiceover for entire briefing script."""
    logger.info(rich_sprint(script))

    if print_script:
      self._print_script_only(script)
      return

    tasks = self._create_tts_tasks(script, output_path)

    logger.info(f"Starting TTS generation for {len(tasks)} script lines")
    await asyncio.gather(*tasks)

    logger.info("TTS generation complete, mastering audio")
    master_briefing_audio(output_path)

  def _print_script_only(self, script: BriefingScript) -> None:
    """Print script without generating audio."""
    for i, line in enumerate(script.lines):
      print(f"Processing part {i}")
      print(line.build_prompt())

  def _create_tts_tasks(self, script: BriefingScript, output_path: Path) -> list:
    """Create TTS tasks for all script lines."""
    rate_limiter = Limiter(self.config.rate_limit_per_minute / 60.0)
    tasks = []

    for i, line in enumerate(script.lines):
      print(f"Processing part {i}")
      print(line.build_prompt())

      task = self.processor.process_script_line(
        line=line,
        part=i,
        output_path=output_path,
        rate_limiter=rate_limiter,
      )
      tasks.append(task)

    return tasks


async def run_voiceover(script: BriefingScript, print_script: bool, output_path: Path) -> None:
  """Main entry point for voiceover generation."""
  orchestrator = TTSOrchestrator()
  await orchestrator.generate_voiceover(script, output_path, print_script)
