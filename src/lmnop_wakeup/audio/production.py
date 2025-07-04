from datetime import date
from pathlib import Path

import structlog
from pydub import AudioSegment

from ..brief.model import ConsolidatedBriefingScript
from ..paths import get_podcast_cover_path
from .id3_tags import BriefingID3Tags, ID3Tagger

logger = structlog.get_logger(__name__)

# Audio production timing constants (all in milliseconds)
_SILENCE_AFTER_BELLS_MS = 5000  # 5 seconds of silence after bells


class AudioProductionMixer:
  """Mixes audio production elements with briefing audio using introduction timing."""

  def mix_audio_with_briefing(
    self,
    briefing_audio_path: Path,
    script: ConsolidatedBriefingScript,
    audio_files_dir: Path,
    output_path: Path,
    briefing_date: date | None = None,
    location_name: str | None = None,
  ) -> Path:
    """
    Mix audio production elements with briefing audio using two-part theme approach.

    Args:
      briefing_audio_path: Path to the main briefing audio file
      script: Briefing script with introduction line tags
      audio_files_dir: Directory containing individual TTS audio files
      output_path: Where to save the final mixed audio

    Returns:
      Path to the output file
    """
    # Get audio resource paths
    from ..paths import get_wakeup_bell_path

    wakeup_bell_path = get_wakeup_bell_path()

    logger.info(
      "Starting audio production mixing",
      briefing_audio=briefing_audio_path,
      wakeup_bell=wakeup_bell_path,
      output=output_path,
      total_segments=len(script.segments),
      intro_segments=[i for i, seg in enumerate(script.segments) if seg.is_introduction],
    )

    # Load audio files
    briefing_audio = AudioSegment.from_file(str(briefing_audio_path))
    wakeup_bell = AudioSegment.from_file(str(wakeup_bell_path))

    logger.debug(
      "Loaded audio files",
      briefing_duration_ms=len(briefing_audio),
      bell_duration_ms=len(wakeup_bell),
    )

    # Create bell sequence
    bell_sequence = self._create_bell_sequence(wakeup_bell)

    # Create the mixed audio with simplified sequence
    mixed_audio = self._create_mixed_audio(briefing_audio, bell_sequence)

    # Export the result
    mixed_audio.export(str(output_path), format="mp3")

    # Add ID3 tags if we have the necessary data
    if briefing_date:
      self._add_id3_tags(output_path, script, briefing_date, location_name)

    logger.info(
      "Audio production mixing completed",
      output_file=output_path,
      final_duration_ms=len(mixed_audio),
    )

    return output_path

  def _create_bell_sequence(self, wakeup_bell: AudioSegment) -> AudioSegment:
    """Create a sequence of 3 bells with intervals."""
    bell_sequence = AudioSegment.empty()

    for i in range(3):
      if i == 0:
        bell_sequence = wakeup_bell
      else:
        # Add 9 seconds between bells
        bell_sequence += AudioSegment.silent(duration=9000) + wakeup_bell

    logger.info(
      "Created bell sequence",
      bell_count=3,
      total_duration_ms=len(bell_sequence),
    )

    return bell_sequence

  def _create_mixed_audio(
    self,
    briefing_audio: AudioSegment,
    bell_sequence: AudioSegment,
  ) -> AudioSegment:
    """Create the final mixed audio with simplified sequence."""

    # Step 1: bells
    mixed_audio = bell_sequence

    # Step 2: silence after bells
    mixed_audio += AudioSegment.silent(duration=_SILENCE_AFTER_BELLS_MS)

    # Step 3: briefing audio
    mixed_audio += briefing_audio

    logger.info(
      "Created mixed audio with simplified sequence",
      bell_duration_ms=len(bell_sequence),
      silence_duration_ms=_SILENCE_AFTER_BELLS_MS,
      briefing_duration_ms=len(briefing_audio),
      total_duration_ms=len(mixed_audio),
    )

    return mixed_audio

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
