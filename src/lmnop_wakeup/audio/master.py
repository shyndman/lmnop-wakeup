from datetime import date
from functools import reduce
from pathlib import Path
from typing import cast

import structlog
from pydub import AudioSegment

from ..brief.model import ConsolidatedBriefingScript
from ..paths import get_podcast_cover_path
from .id3_tags import BriefingID3Tags, ID3Tagger

logger = structlog.get_logger()


class AudioMaster:
  def master_briefing_audio(
    self,
    path: Path,
    script: ConsolidatedBriefingScript | None = None,
    briefing_date: date | None = None,
    location_name: str | None = None,
  ) -> Path:
    """Master briefing audio by combining all WAV files into a single MP3 with ID3 tags."""
    wav_files = self._find_and_sort_wav_files(path)
    if not wav_files:
      logger.warning(f"No WAV files found in {path}")
      raise ValueError(f"No WAV files found in {path}")

    combined_audio = self._combine_audio_segments(wav_files)
    output_path = self._export_master_audio(combined_audio, path)

    # Add ID3 tags if we have the necessary data
    if script and briefing_date:
      self._add_id3_tags(output_path, script, briefing_date, location_name)

    logger.info(f"Mastered {len(wav_files)} audio files to {output_path}")
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
    output_path = output_dir / "briefing.mp3"
    combined_audio.export(output_path, format="mp3")
    return output_path

  def _add_id3_tags(
    self,
    audio_path: Path,
    script: ConsolidatedBriefingScript,
    briefing_date: date,
    location_name: str | None = None,
  ) -> None:
    """Add ID3 tags to the audio file."""
    try:
      tags = BriefingID3Tags.from_briefing_data(briefing_date, script, location_name)
      tagger = ID3Tagger()

      # Try to get the cover image
      cover_path = None
      try:
        cover_path = get_podcast_cover_path()
        if not cover_path.exists():
          logger.warning(f"Podcast cover not found at {cover_path}")
          cover_path = None
      except Exception as e:
        logger.warning(f"Could not load podcast cover: {e}")

      tagger.add_tags_to_file(audio_path, tags, cover_path)
    except Exception as e:
      logger.error(f"Failed to add ID3 tags: {e}")


def master_briefing_audio(
  path: Path,
  script: ConsolidatedBriefingScript | None = None,
  briefing_date: date | None = None,
  location_name: str | None = None,
) -> Path:
  """Convenience function for mastering briefing audio with optional ID3 tagging."""
  master = AudioMaster()
  return master.master_briefing_audio(path, script, briefing_date, location_name)
