import wave
from pathlib import Path

import structlog

logger = structlog.get_logger()


class AudioFileManager:
  def __init__(self, channels: int = 1, rate: int = 24000, sample_width: int = 2):
    self.channels = channels
    self.rate = rate
    self.sample_width = sample_width

  def create_wave_file(self, filename: str | Path, pcm_data: bytes) -> None:
    """Create a WAV file from PCM data."""
    with wave.open(str(filename), "wb") as wf:
      wf.setnchannels(self.channels)
      wf.setsampwidth(self.sample_width)
      wf.setframerate(self.rate)
      wf.writeframes(pcm_data)

    logger.debug(f"Created WAV file {filename}")
