from google.genai import types
from loguru import logger

from lmnop_wakeup.brief.actors import voice_for_speaker


class SpeechConfigBuilder:
  def build_config(self, speakers: set[str]) -> types.SpeechConfig:
    """Build speech configuration based on number of speakers."""
    if len(speakers) == 1:
      return self._build_single_speaker_config(next(iter(speakers)))
    elif len(speakers) == 2:
      return self._build_multi_speaker_config(speakers)
    else:
      raise ValueError(f"Expected 1 or 2 speakers, got {len(speakers)}: {', '.join(speakers)}")

  def _build_single_speaker_config(self, speaker: str) -> types.SpeechConfig:
    """Build configuration for single speaker."""
    voice_name = voice_for_speaker(speaker)
    logger.debug(
      "Building single speaker config for {speaker} with voice {voice}",
      speaker=speaker,
      voice=voice_name,
    )

    return types.SpeechConfig(
      voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
      )
    )

  def _build_multi_speaker_config(self, speakers: set[str]) -> types.SpeechConfig:
    """Build configuration for multiple speakers."""
    logger.debug(
      "Building multi-speaker config for speakers: {speakers}", speakers=", ".join(speakers)
    )

    speaker_configs = []
    for speaker in speakers:
      voice_name = voice_for_speaker(speaker)
      speaker_configs.append(
        types.SpeakerVoiceConfig(
          speaker=speaker,
          voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
          ),
        )
      )

    return types.SpeechConfig(
      multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
        speaker_voice_configs=speaker_configs
      )
    )
