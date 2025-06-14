import dataclasses
from pathlib import Path

import structlog
from pydub import AudioSegment

from ..brief.model import ConsolidatedBriefingScript

logger = structlog.get_logger(__name__)


@dataclasses.dataclass
class AudioProductionConfig:
  """Configuration for audio production mixing."""

  # Bell sequence settings
  bell_count: int = 3  # Number of bell rings
  bell_interval_ms: int = 10000  # 10 seconds between bells

  # Theme music settings
  background_volume_reduction_db: int = -20  # Reduce theme volume during dialog overlay


class AudioProductionMixer:
  """Mixes audio production elements with briefing audio using introduction timing."""

  def __init__(self, config: AudioProductionConfig | None = None):
    self.config = config or AudioProductionConfig()

  def mix_audio_with_briefing(
    self,
    briefing_audio_path: Path,
    script: ConsolidatedBriefingScript,
    audio_files_dir: Path,
    output_path: Path,
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
    from ..paths import get_theme_intro_path, get_theme_music_path, get_wakeup_bell_path

    theme_music_path = get_theme_music_path()
    theme_intro_path = get_theme_intro_path()
    wakeup_bell_path = get_wakeup_bell_path()

    logger.info(
      "Starting audio production mixing",
      briefing_audio=briefing_audio_path,
      theme_music=theme_music_path,
      theme_intro=theme_intro_path,
      wakeup_bell=wakeup_bell_path,
      output=output_path,
    )

    # Check if all required audio files exist
    if (
      not theme_music_path.exists()
      or not theme_intro_path.exists()
      or not wakeup_bell_path.exists()
    ):
      raise FileNotFoundError(
        f"Audio production files not found (theme: {theme_music_path.exists()}, "
        f"intro: {theme_intro_path.exists()}, bell: {wakeup_bell_path.exists()})"
      )

    # Load audio files
    briefing_audio = AudioSegment.from_file(str(briefing_audio_path))
    theme_music = AudioSegment.from_file(str(theme_music_path))
    theme_intro = AudioSegment.from_file(str(theme_intro_path))
    wakeup_bell = AudioSegment.from_file(str(wakeup_bell_path))

    # Calculate introduction timing (for speech split logic)
    intro_duration_ms = self._calculate_intro_duration(script, audio_files_dir)

    logger.info(
      "Calculated introduction timing",
      intro_duration_ms=intro_duration_ms,
      theme_intro_duration_ms=len(theme_intro),
    )

    # Create bell sequence
    bell_sequence = self._create_bell_sequence(wakeup_bell)

    # Create the mixed audio with new sequence
    mixed_audio = self._create_mixed_audio(
      briefing_audio, theme_intro, theme_music, intro_duration_ms, bell_sequence
    )

    # Export the result
    mixed_audio.export(str(output_path), format="mp3")

    logger.info(
      "Audio production mixing completed",
      output_file=output_path,
      final_duration_ms=len(mixed_audio),
    )

    return output_path

  def _create_bell_sequence(self, wakeup_bell: AudioSegment) -> AudioSegment:
    """Create a sequence of 4 bells, 10 seconds apart, starting at time 0."""
    bell_sequence = AudioSegment.empty()

    for i in range(self.config.bell_count):
      # Add silence to position this bell at the correct time
      bell_position_ms = i * self.config.bell_interval_ms

      if i == 0:
        # First bell starts immediately
        bell_sequence = wakeup_bell
      else:
        # Calculate silence needed before this bell
        silence_duration = bell_position_ms - len(bell_sequence)
        bell_sequence += AudioSegment.silent(duration=silence_duration) + wakeup_bell

    logger.info(
      "Created bell sequence",
      bell_count=self.config.bell_count,
      total_duration_ms=len(bell_sequence),
      interval_ms=self.config.bell_interval_ms,
    )

    return bell_sequence

  def _calculate_intro_duration(
    self, script: "ConsolidatedBriefingScript", audio_files_dir: Path
  ) -> int:
    """Calculate intro duration for a consolidated script."""
    total_duration_ms = 0

    for segment_index, segment in enumerate(script.segments):
      if not segment.is_introduction:
        # Skip segments that are not marked as introduction
        continue

      # Get the audio duration for this segment
      audio_file = audio_files_dir / f"{segment_index}.wav"
      if audio_file.exists():
        segment_audio = AudioSegment.from_wav(str(audio_file))
        total_duration_ms += len(segment_audio)
        logger.debug(
          "Added intro segment duration",
          segment_index=segment_index,
          duration_ms=len(segment_audio),
        )
      else:
        logger.warning(
          "Audio file not found for intro segment",
          segment_index=segment_index,
          expected_file=audio_file,
        )

    return total_duration_ms

  def _create_mixed_audio(
    self,
    briefing_audio: AudioSegment,
    theme_intro: AudioSegment,
    theme_music: AudioSegment,
    intro_duration_ms: int,
    bell_sequence: AudioSegment,
  ) -> AudioSegment:
    """Create the final mixed audio with 9-step sequence."""

    # Step 1: bells
    mixed_audio = bell_sequence

    # Step 2: 15 seconds of silence
    mixed_audio += AudioSegment.silent(duration=15000)

    # Step 3: theme intro
    mixed_audio += theme_intro

    # Steps 4-8: theme music with dialog overlay
    dialog_duration_ms = len(briefing_audio)
    minimum_theme_duration_ms = 3000 + dialog_duration_ms + 2000

    theme_music_duration_ms = len(theme_music)
    iterations_needed = (
      minimum_theme_duration_ms + theme_music_duration_ms - 1
    ) // theme_music_duration_ms

    extended_theme = theme_music * iterations_needed

    theme_with_dialog = extended_theme.overlay(
      briefing_audio, position=3000, gain_during_overlay=self.config.background_volume_reduction_db
    )

    mixed_audio += theme_with_dialog

    # Step 9: continue on to rest of show (no additional content in this implementation)

    logger.info(
      "Created mixed audio with 9-step sequence",
      bell_duration_ms=len(bell_sequence),
      silence_duration_ms=15000,
      theme_intro_duration_ms=len(theme_intro),
      theme_with_dialog_duration_ms=len(theme_with_dialog),
      total_duration_ms=len(mixed_audio),
    )

    return mixed_audio
