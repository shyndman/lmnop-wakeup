from functools import reduce
from pathlib import Path
from typing import cast

from loguru import logger
from pydub import AudioSegment


class AudioMaster:
  def master_briefing_audio(self, path: Path) -> Path:
    """Master briefing audio by combining all WAV files into a single MP3."""
    wav_files = self._find_and_sort_wav_files(path)
    if not wav_files:
      logger.warning("No WAV files found in {path}", path=path)
      raise ValueError(f"No WAV files found in {path}")

    combined_audio = self._combine_audio_segments(wav_files)
    output_path = self._export_master_audio(combined_audio, path)

    logger.info(
      "Mastered {count} audio files to {output_path}", count=len(wav_files), output_path=output_path
    )
    return output_path

  def _find_and_sort_wav_files(self, path: Path) -> list[Path]:
    """Find and sort WAV files by numeric filename."""
    wav_files = list(path.glob("*.wav"))
    wav_files.sort(key=lambda f: int(f.stem))
    return wav_files

  def _combine_audio_segments(self, wav_files: list[Path]) -> AudioSegment:
    """Combine multiple WAV files into a single audio segment."""
    audio_segments = cast(
      list[AudioSegment], map(lambda wav: AudioSegment.from_wav(str(wav)), wav_files)
    )
    return reduce(lambda x, y: x + y, audio_segments)

  def _export_master_audio(self, combined_audio: AudioSegment, output_dir: Path) -> Path:
    """Export combined audio to MP3 format."""
    output_path = output_dir / "master_briefing.mp3"
    combined_audio.export(output_path, "mp3")
    return output_path


def master_briefing_audio(path: Path) -> Path:
  """Convenience function for mastering briefing audio."""
  master = AudioMaster()
  return master.master_briefing_audio(path)
