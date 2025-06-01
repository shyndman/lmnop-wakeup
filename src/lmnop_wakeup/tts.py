import asyncio
import wave
from pathlib import Path

import rich
from google import genai
from google.genai import types
from loguru import logger

from lmnop_wakeup.audio.master import master_briefing_audio
from lmnop_wakeup.brief.actors import voice_for_speaker
from lmnop_wakeup.brief.model import BriefingScript
from lmnop_wakeup.core.logging import rich_sprint
from lmnop_wakeup.core.typing import assert_not_none, ensure
from lmnop_wakeup.env import get_litellm_api_key, get_litellm_base_url


async def run_tts(
  client: genai.client.AsyncClient, prompt: str, part: int, speakers: set[str], output_path: Path
):
  # Set up the wave file to save the output:
  def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

  if len(speakers) == 1:
    speech_config = types.SpeechConfig(
      voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(
          voice_name=voice_for_speaker(assert_not_none(list(speakers))[0]),
        )
      )
    )
  elif len(speakers) == 2:
    speech_config = types.SpeechConfig(
      multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
        speaker_voice_configs=[
          types.SpeakerVoiceConfig(
            speaker=slug,
            voice_config=types.VoiceConfig(
              prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=voice_for_speaker(slug),
              )
            ),
          )
          for slug in speakers
        ],
      )
    )
  else:
    raise ValueError(f"Expected 1 or 2 speakers, got {len(speakers)}: {', '.join(speakers)}")

  response = await client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=prompt,
    config=types.GenerateContentConfig(
      response_modalities=["AUDIO"],
      speech_config=speech_config,
      temperature=0.95,
      top_p=0.95,
    ),
  )

  candidates = ensure(response.candidates)
  content = ensure(candidates[0].content)
  parts = ensure(content.parts)
  inline_data = ensure(parts[0].inline_data)
  data = ensure(inline_data.data)

  file_name = output_path / f"{part}.wav"
  wave_file(str(file_name.absolute()), data)  # Saves the file to current directory


async def run_voiceover(script: BriefingScript, print_script: bool, output_path: Path):
  # Implement the voiceover functionality here
  logger.info(rich_sprint(script))

  cleaned_script = script.clean_script()

  client = genai.Client(
    api_key=get_litellm_api_key(),
    http_options={
      "base_url": get_litellm_base_url(),
    },
  )

  logger.info(rich_sprint(cleaned_script))
  tasks = []
  for i, dialogue_group in enumerate(script.dialogue_groups()):
    print(f"Processing part {i}")
    print(dialogue_group.build_prompt())
    if not print_script:
      tasks.append(
        run_tts(
          client.aio,
          prompt=dialogue_group.build_prompt(),
          part=i,
          speakers=dialogue_group.character_slugs,
          output_path=output_path,
        ),
      )

  rich.print(tasks)
  await asyncio.gather(*tasks)

  master_briefing_audio(output_path)
