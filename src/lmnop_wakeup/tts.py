import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import rich
import structlog
from asynciolimiter import Limiter
from google import genai
from google.genai import types
from pydub import AudioSegment

from lmnop_wakeup.audio.config import TTSConfig
from lmnop_wakeup.audio.file_manager import AudioFileManager
from lmnop_wakeup.audio.master import master_briefing_audio
from lmnop_wakeup.audio.speech_config import SpeechConfigBuilder
from lmnop_wakeup.brief.model import (
  BriefingScript,
  ConsolidatedBriefingScript,
  ScriptLine,
  SpeakerSegment,
)
from lmnop_wakeup.core.cost_tracking import AgentCost, CostCategory
from lmnop_wakeup.core.logging import rich_sprint
from lmnop_wakeup.core.typing import assert_not_none, ensure
from lmnop_wakeup.env import get_litellm_api_key, get_litellm_base_url

logger = structlog.get_logger(__name__)


def calculate_words_per_minute(text: str, audio_file_path: Path) -> float:
  """Calculate words per minute for given text and corresponding audio file.

  Args:
      text: The text that was converted to speech
      audio_file_path: Path to the generated WAV file

  Returns:
      Words per minute as a float
  """
  # Count words in the text (simple whitespace splitting)
  word_count = len(text.split())

  # Get audio duration using pydub
  audio = AudioSegment.from_wav(str(audio_file_path))
  duration_minutes = len(audio) / 1000.0 / 60.0  # Convert milliseconds to minutes

  if duration_minutes == 0:
    logger.warning(f"Audio file {audio_file_path} has zero duration")
    return 0.0

  wpm = word_count / duration_minutes

  logger.debug(
    "WPM calculation",
    text_length=len(text),
    word_count=word_count,
    duration_seconds=len(audio) / 1000.0,
    wpm=round(wpm, 1),
    file=audio_file_path.name,
  )

  return wpm


def calculate_tts_cost(model_name: str, input_tokens: int, output_tokens: int) -> Decimal:
  """Calculate the cost of a TTS request based on model and token usage.

  Args:
      model_name: The Gemini model used (e.g., "gemini-2.5-pro-preview-tts")
      input_tokens: Number of input tokens used
      output_tokens: Number of output tokens used

  Returns:
      Total cost in USD as Decimal for precise calculations
  """
  # Pricing per 1M tokens as of Dec 2024
  pricing = {
    "gemini-2.5-flash-preview-tts": {
      "input_per_1m": Decimal("0.50"),
      "output_per_1m": Decimal("10.00"),
    },
    "gemini-2.5-pro-preview-tts": {
      "input_per_1m": Decimal("1.00"),
      "output_per_1m": Decimal("20.00"),
    },
  }

  # Normalize model name to handle variations
  model_key = model_name.lower()
  if model_key not in pricing:
    logger.warning(f"Unknown model for pricing: {model_name}, using Pro pricing as fallback")
    model_key = "gemini-2.5-pro-preview-tts"

  rates = pricing[model_key]

  # Calculate cost (tokens / 1M * price_per_1M) using Decimal for precision
  input_cost = (Decimal(input_tokens) / Decimal("1000000")) * rates["input_per_1m"]
  output_cost = (Decimal(output_tokens) / Decimal("1000000")) * rates["output_per_1m"]
  total_cost = input_cost + output_cost

  logger.debug(
    "TTS cost calculation",
    model=model_name,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    input_cost_usd=float(input_cost.quantize(Decimal("0.000001"))),
    output_cost_usd=float(output_cost.quantize(Decimal("0.000001"))),
    total_cost_usd=float(total_cost.quantize(Decimal("0.000001"))),
  )

  return total_cost


def calculate_overall_statistics(output_path: Path) -> dict[str, float]:
  """Calculate overall statistics for all generated WAV files in a directory.

  Args:
      output_path: Directory containing numbered WAV files

  Returns:
      Dictionary with statistics: total_files, total_duration_minutes
  """
  wav_files = sorted(output_path.glob("*.wav"), key=lambda f: int(f.stem))

  if not wav_files:
    logger.warning(f"No WAV files found in {output_path}")
    return {"total_files": 0, "total_duration_minutes": 0.0}

  total_duration_ms = 0

  for wav_file in wav_files:
    try:
      audio = AudioSegment.from_wav(str(wav_file))
      total_duration_ms += len(audio)
    except Exception as e:
      logger.warning(f"Could not process {wav_file}: {e}")
      continue

  total_duration_minutes = total_duration_ms / 1000.0 / 60.0

  return {
    "total_files": len(wav_files),
    "total_duration_minutes": round(total_duration_minutes, 2),
  }


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
  ) -> AgentCost:
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

    # Calculate cost from usage metadata
    usage = response.usage_metadata
    if usage is None:
      raise ValueError("Missing usage metadata")

    cost_usd = calculate_tts_cost(
      self.config.model_name,
      assert_not_none(usage.prompt_token_count),
      usage.candidates_token_count or 0,
    )

    # Create cost record
    agent_cost = AgentCost(
      agent_name=f"tts-{line.character_slug}",
      model_name=self.config.model_name,
      input_tokens=assert_not_none(usage.prompt_token_count),
      output_tokens=usage.candidates_token_count or 0,
      cost_usd=cost_usd,
      timestamp=datetime.now(),
      category=CostCategory.TTS,
      metadata={"character": line.character_slug, "part": part},
    )

    # Extract audio data
    candidates = ensure(response.candidates)
    content = ensure(candidates[0].content)
    parts = ensure(content.parts)
    inline_data = ensure(parts[0].inline_data)
    audio_data = ensure(inline_data.data)

    # Save to file
    output_file = output_path / f"{part}.wav"
    self.file_manager.create_wave_file(output_file, audio_data)

    # Calculate and log words per minute and cost
    wpm = calculate_words_per_minute(line.text, output_file)
    logger.info(
      f"TTS call completed: tts-{line.character_slug}",
      agent=f"tts-{line.character_slug}",
      model=self.config.model_name,
      cost_usd=float(cost_usd.quantize(Decimal("0.000001"))),
      input_tokens=agent_cost.input_tokens,
      output_tokens=agent_cost.output_tokens,
      total_tokens=agent_cost.input_tokens + agent_cost.output_tokens,
      wpm=round(wpm, 1),
      part=part,
      character=line.character_slug,
    )

    return agent_cost

  async def process_speaker_segment(
    self,
    segment: SpeakerSegment,
    part: int,
    output_path: Path,
    rate_limiter: Limiter,
  ) -> AgentCost:
    """Process a speaker segment into audio using multi-speaker TTS."""
    speech_config = self.speech_config_builder.build_config(segment.speakers)

    await rate_limiter.wait()

    speakers_str = ", ".join(segment.speakers)
    logger.info(
      f"Processing TTS for segment {part} with {segment.character_count} speakers: {speakers_str}"
    )

    response = await self.client.aio.models.generate_content(
      model=self.config.model_name,
      contents=segment.build_prompt(),
      config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=speech_config,
        temperature=self.config.temperature,
        top_p=self.config.top_p,
      ),
    )

    rich.print(response.usage_metadata)

    # Calculate cost from usage metadata
    usage = response.usage_metadata
    if not usage:
      raise ValueError("Missing usage metadata")
    cost_usd = calculate_tts_cost(
      self.config.model_name,
      assert_not_none(usage.prompt_token_count),
      usage.candidates_token_count or 0,
    )

    speakers_str = ", ".join(segment.speakers)
    # Create cost record
    agent_cost = AgentCost(
      agent_name="tts-segment",
      model_name=self.config.model_name,
      input_tokens=assert_not_none(usage.prompt_token_count),
      output_tokens=usage.candidates_token_count or 0,
      cost_usd=cost_usd,
      timestamp=datetime.now(),
      category=CostCategory.TTS,
      metadata={"speakers": speakers_str, "part": part, "character_count": segment.character_count},
    )

    # Extract audio data
    candidates = ensure(response.candidates)
    content = ensure(candidates[0].content)
    parts = ensure(content.parts)
    inline_data = ensure(parts[0].inline_data)
    audio_data = ensure(inline_data.data)

    # Save to file
    output_file = output_path / f"{part}.wav"
    self.file_manager.create_wave_file(output_file, audio_data)

    # Calculate and log words per minute and cost for the segment
    # Combine text from all lines in the segment
    combined_text = " ".join(line.text for line in segment.lines)
    wpm = calculate_words_per_minute(combined_text, output_file)
    logger.info(
      "TTS call completed: tts-segment",
      agent="tts-segment",
      model=self.config.model_name,
      cost_usd=float(cost_usd.quantize(Decimal("0.000001"))),
      input_tokens=agent_cost.input_tokens,
      output_tokens=agent_cost.output_tokens,
      total_tokens=agent_cost.input_tokens + agent_cost.output_tokens,
      wpm=round(wpm, 1),
      part=part,
      speakers=speakers_str,
      character_count=segment.character_count,
    )

    return agent_cost


class TTSOrchestrator:
  def __init__(self, config: TTSConfig | None = None):
    self.config = config or TTSConfig()
    self.processor = TTSProcessor(self.config)
    self.agent_costs: list[AgentCost] = []

  async def generate_individual_tts_files(
    self, script: BriefingScript | ConsolidatedBriefingScript, output_path: Path
  ) -> None:
    """Generate individual TTS audio files for script lines or segments."""
    logger.info(rich_sprint(script))

    if isinstance(script, ConsolidatedBriefingScript):
      tasks = self._create_segment_tasks(script, output_path)
      logger.info(f"Starting TTS generation for {len(tasks)} speaker segments")
    else:
      tasks = self._create_tts_tasks(script, output_path)
      logger.info(f"Starting TTS generation for {len(tasks)} script lines")

    agent_costs = await asyncio.gather(*tasks)
    self.agent_costs = agent_costs
    total_cost = sum(cost.cost_usd for cost in agent_costs)

    # Log overall statistics with cost
    stats = calculate_overall_statistics(output_path)
    total_files = stats["total_files"]
    total_duration = stats["total_duration_minutes"]
    logger.info(f"TTS complete: {total_files} files, {total_duration} min, ${total_cost:.4f}")

  async def generate_voiceover(
    self,
    script: BriefingScript | ConsolidatedBriefingScript,
    output_path: Path,
    print_script: bool = False,
  ) -> None:
    """Generate voiceover for entire briefing script."""
    if print_script:
      self._print_script_only(script)
      return

    await self.generate_individual_tts_files(script, output_path)

    logger.info("TTS generation complete, mastering audio")
    master_briefing_audio(output_path)

  def _print_script_only(self, script: BriefingScript | ConsolidatedBriefingScript) -> None:
    """Print script without generating audio."""
    if isinstance(script, ConsolidatedBriefingScript):
      for i, segment in enumerate(script.segments):
        print(f"Processing segment {i}")
        print(segment.build_prompt())
    else:
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

  def _create_segment_tasks(self, script: ConsolidatedBriefingScript, output_path: Path) -> list:
    """Create TTS tasks for all speaker segments."""
    rate_limiter = Limiter(self.config.rate_limit_per_minute / 60.0)
    tasks = []

    for i, segment in enumerate(script.segments):
      print(f"Processing segment {i}")
      print(segment.build_prompt())

      task = self.processor.process_speaker_segment(
        segment=segment,
        part=i,
        output_path=output_path,
        rate_limiter=rate_limiter,
      )
      tasks.append(task)

    return tasks


async def run_voiceover(
  script: BriefingScript | ConsolidatedBriefingScript, print_script: bool, output_path: Path
) -> None:
  """Main entry point for voiceover generation."""
  orchestrator = TTSOrchestrator()
  await orchestrator.generate_voiceover(script, output_path, print_script)
