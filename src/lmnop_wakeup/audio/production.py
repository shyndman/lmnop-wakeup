import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from pydub import AudioSegment

if TYPE_CHECKING:
  from ..brief.model import BriefingScript, ConsolidatedBriefingScript

logger = structlog.get_logger(__name__)


@dataclasses.dataclass
class AudioProductionConfig:
  """Configuration for audio production mixing."""

  background_volume_reduction_db: int = -12  # Reduce theme volume by 12dB during speech
  fade_out_duration_ms: int = 2000  # Fade out over 2 seconds
  intro_buffer_ms: int = 500  # Extra time after intro content for fade completion


class AudioProductionMixer:
  """Mixes audio production elements with briefing audio using introduction timing."""

  def __init__(self, config: AudioProductionConfig | None = None):
    self.config = config or AudioProductionConfig()

  def mix_audio_with_briefing(
    self,
    briefing_audio_path: Path,
    theme_music_path: Path,
    theme_intro_path: Path,
    script: "BriefingScript | ConsolidatedBriefingScript",
    audio_files_dir: Path,
    output_path: Path,
  ) -> Path:
    """
    Mix audio production elements with briefing audio using two-part theme approach.

    Args:
      briefing_audio_path: Path to the main briefing audio file
      theme_music_path: Path to the looping theme music MP3 file
      theme_intro_path: Path to the theme intro MP3 file (plays before speech)
      script: Briefing script with introduction line tags
      audio_files_dir: Directory containing individual TTS audio files
      output_path: Where to save the final mixed audio

    Returns:
      Path to the output file
    """
    logger.info(
      "Starting audio production mixing",
      briefing_audio=briefing_audio_path,
      theme_music=theme_music_path,
      theme_intro=theme_intro_path,
      output=output_path,
    )

    # Load audio files
    briefing_audio = AudioSegment.from_file(str(briefing_audio_path))
    theme_music = AudioSegment.from_file(str(theme_music_path))
    theme_intro = AudioSegment.from_file(str(theme_intro_path))

    # Calculate introduction timing
    intro_duration_ms = self._calculate_intro_duration(script, audio_files_dir)

    # Get intro segment duration from the actual file
    intro_lead_in_ms = len(theme_intro)

    logger.info(
      "Calculated introduction timing",
      intro_duration_ms=intro_duration_ms,
      intro_lead_in_ms=intro_lead_in_ms,
      fade_out_ms=self.config.fade_out_duration_ms,
    )

    # Calculate theme background music duration needed
    theme_background_duration_needed = (
      intro_duration_ms + self.config.intro_buffer_ms + self.config.fade_out_duration_ms
    )

    # Prepare theme background music segment
    theme_background_segment = self._prepare_theme_segment(
      theme_music, theme_background_duration_needed
    )

    # Create the mixed audio
    mixed_audio = self._create_mixed_audio(
      briefing_audio, theme_intro, theme_background_segment, intro_duration_ms
    )

    # Export the result
    mixed_audio.export(str(output_path), format="mp3")

    logger.info(
      "Audio production mixing completed",
      output_file=output_path,
      final_duration_ms=len(mixed_audio),
    )

    return output_path

  def _calculate_intro_duration(
    self, script: "BriefingScript | ConsolidatedBriefingScript", audio_files_dir: Path
  ) -> int:
    """
    Calculate the total duration of introduction content in milliseconds.

    For consolidated scripts, we need to map introduction lines to their
    corresponding audio segments and sum the durations.
    """
    from ..brief.model import ConsolidatedBriefingScript

    if isinstance(script, ConsolidatedBriefingScript):
      return self._calculate_intro_duration_consolidated(script, audio_files_dir)
    else:
      return self._calculate_intro_duration_original(script, audio_files_dir)

  def _calculate_intro_duration_consolidated(
    self, script: "ConsolidatedBriefingScript", audio_files_dir: Path
  ) -> int:
    """Calculate intro duration for a consolidated script."""
    total_duration_ms = 0

    for segment_index, segment in enumerate(script.segments):
      # Check if this segment is marked as introduction
      if segment.is_introduction:
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

  def _calculate_intro_duration_original(
    self, script: "BriefingScript", audio_files_dir: Path
  ) -> int:
    """
    Calculate intro duration for an original (non-consolidated) script.

    This is more complex as we need to map original lines to consolidated segments.
    For now, we'll use a simple estimation based on intro line count.
    """
    intro_lines = [line for line in script.lines if line.is_introduction]

    if not intro_lines:
      logger.warning("No introduction lines found in script")
      return 0

    # Estimate average line duration by sampling existing audio files
    audio_files = sorted(audio_files_dir.glob("*.wav"), key=lambda f: int(f.stem))

    if not audio_files:
      logger.warning("No audio files found for duration estimation")
      return 5000  # Default to 5 seconds

    # Sample the first few audio files to estimate average line duration
    sample_size = min(3, len(audio_files))
    total_sample_duration = 0

    for audio_file in audio_files[:sample_size]:
      audio = AudioSegment.from_wav(str(audio_file))
      total_sample_duration += len(audio)

    avg_duration_per_segment = total_sample_duration / sample_size

    # Estimate intro duration (this is rough but workable for first iteration)
    estimated_intro_duration = int(avg_duration_per_segment * len(intro_lines) * 0.5)

    logger.info(
      "Estimated intro duration from line count",
      intro_lines=len(intro_lines),
      avg_segment_duration=avg_duration_per_segment,
      estimated_duration=estimated_intro_duration,
    )

    return estimated_intro_duration

  def _prepare_theme_segment(self, theme_music: AudioSegment, duration_needed: int) -> AudioSegment:
    """Prepare theme music segment of the required duration."""
    if len(theme_music) >= duration_needed:
      # Trim to needed length
      return theme_music[:duration_needed]
    else:
      # Loop the theme music to reach needed duration
      loops_needed = (duration_needed // len(theme_music)) + 1

      # Build looped theme by concatenating segments
      looped_theme = AudioSegment.empty()
      for _ in range(loops_needed):
        looped_theme += theme_music

      return looped_theme[:duration_needed]

  def _create_mixed_audio(
    self,
    briefing_audio: AudioSegment,
    theme_intro: AudioSegment,
    theme_background_segment: AudioSegment,
    intro_duration_ms: int,
  ) -> AudioSegment:
    """Create the final mixed audio with theme intro and background music."""

    # Phase 1: Theme intro alone (no speech)
    intro_lead_in_duration = len(theme_intro)

    # Phase 2: Theme background music with speech (during intro content)
    speech_start = intro_lead_in_duration
    intro_end = speech_start + intro_duration_ms + self.config.intro_buffer_ms

    # Phase 3: Fade out theme background music
    fade_start = intro_end - speech_start  # Relative to theme_background_segment start
    fade_end = fade_start + self.config.fade_out_duration_ms

    # Apply volume reduction to background theme during speech
    theme_background_during_speech = (
      theme_background_segment[:fade_start] + self.config.background_volume_reduction_db
    )

    # Apply fade out to the background theme music ending
    theme_background_fade_out = theme_background_segment[fade_start:fade_end].fade_out(
      self.config.fade_out_duration_ms
    )

    # Combine background theme segments
    final_background_theme = theme_background_during_speech + theme_background_fade_out

    # Create the complete audio sequence:
    # 1. Start with theme intro (full volume, no speech)
    # 2. Add background theme with speech overlaid
    mixed_audio = theme_intro + briefing_audio.overlay(final_background_theme)

    return mixed_audio
