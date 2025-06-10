from io import StringIO

import structlog
from pydantic import BaseModel, Field


class Character(BaseModel):
  slug: str
  name: str
  pronouns: str
  voice: str
  personality: str
  specialty: str
  script_writer_instructions: str


class CharacterPool(BaseModel):
  pool: list[Character] = []


class ScriptLine(BaseModel):
  """
  A single line of dialogue spoken by one character.

  This represents one character's spoken text within a conversation. Each line
  should be a complete thought or statement, but can be interrupted or responded
  to by other characters in the same tonal grouping.

  Examples:
    ScriptLine(
      character_slug="sarah",
      text="Well folks, it's looking like a beautiful day ahead!",
      character_style_direction="sound professionally efficient with a brisk, informative pace",
    )
    ScriptLine(
      character_slug="marcus",
      text="Hold on Sarah, have you seen the storm brewing?",
      character_style_direction="sound concerned and urgent",
    )
  """

  character_slug: str = Field(..., description="Character identifier from the character pool")

  character_style_direction: str = Field(
    ..., description="Detailed emotional and stylistic direction for character_1", min_length=15
  )

  text: str = Field(..., description="Dialogue text maintaining character voice", min_length=1)

  def build_prompt(self) -> str:
    sb = StringIO()
    # character = character_for_slug(self.character_1_slug)
    sb.write(f"{self.character_slug} is {self.character_style_direction}: ")
    sb.write(f"{self.text}\n\n")

    return sb.getvalue()


class SpeakerSegment(BaseModel):
  """
  A segment of consecutive script lines optimized for multi-speaker TTS generation.

  Groups lines by speaker combinations (1-2 speakers) to minimize API calls
  while respecting the 2-speaker limit of Gemini's multi-speaker TTS.
  """

  lines: list[ScriptLine] = Field(..., description="Consecutive script lines in this segment")
  character_1_slug: str = Field(..., description="Primary character in this segment")
  character_1_style_direction: str = Field(..., description="Style direction for character 1")
  character_2_slug: str | None = Field(default=None, description="Secondary character (if present)")
  character_2_style_direction: str | None = Field(
    default=None, description="Style direction for character 2"
  )

  @property
  def character_count(self) -> int:
    """Number of unique characters in this segment."""
    return 1 if self.character_2_slug is None else 2

  @property
  def speakers(self) -> set[str]:
    """Set of unique speakers in this segment."""
    if self.character_2_slug is None:
      return {self.character_1_slug}
    return {self.character_1_slug, self.character_2_slug}

  def build_prompt(self) -> str:
    """Build a prompt for TTS generation using your proven format."""
    sb = StringIO()

    if self.character_count == 1:
      # character = character_for_slug(self.character_1_slug)
      sb.write(f"{self.character_1_slug} is {self.character_1_style_direction}: ")
      for line in self.lines:
        sb.write(f"{line.text}\n\n")
    elif self.character_count == 2:
      sb.write(f"{self.character_1_slug} is {self.character_1_style_direction}")
      sb.write(f", and {self.character_2_slug} is {self.character_2_style_direction}:\n\n")
      for line in self.lines:
        sb.write(f"{line.character_slug}: {line.text}\n\n")

    return sb.getvalue()


class ScriptSection(BaseModel):
  """
  A logical section of the briefing script covering related content.

  Sections help organize the briefing into coherent segments (e.g., "Weather Update",
  "Traffic Report", "Top News Stories"). Each section contains multiple tonal dialogue
  groups, allowing for natural emotional variation within the same topic area.

  Examples:
      - "Morning Weather" section with upbeat weather discussion
      - "Breaking News" section with serious, concerned dialogue
      - "Community Events" section with enthusiastic, promotional tone
  """

  name: str = Field(..., description="Descriptive name for this section", min_length=1)

  lines: list[ScriptLine] = Field(
    ..., description="Ordered list of spoken lines within this section", min_length=1
  )


class BriefingScript(BaseModel):
  """
  Complete multi-character script for a morning briefing.

  This is the top-level structure that represents the entire briefing transformed
  from outline format into conversational script format. The script is organized
  into sections, each containing dialogue groups optimized for efficient processing
  through multi-speaker text-to-speech APIs.

  Key requirements:
  - Must cover ALL sections from the briefing outline
  - Must include ALL high-priority events from prioritized events
  - Should feel like natural conversation, not formal presentation
  - Characters should maintain distinct personalities throughout
  - Dialogue should bounce between characters naturally (no monologues)
  - Target length should match briefing outline specifications (typically 3-5 minutes)

  Usage:
      The generated script will be processed section by section, with each
      tonal dialogue group making a single API call to the speech synthesis service.
  """

  sections: list[ScriptSection] = Field(
    default=[], description="Ordered list of briefing sections", min_length=1
  )

  def get_all_characters(self) -> set[str]:
    """Extract all unique character slugs used in the script."""
    return {line.character_slug for section in self.sections for line in section.lines}

  @property
  def lines(self) -> list[ScriptLine]:
    """
    Flatten all script lines into a single list for easy processing.

    This provides a simple way to iterate over all dialogue lines in the script
    without needing to navigate through sections.
    """
    return [line for section in self.sections for line in section.lines]

  def consolidate_dialogue(self) -> "ConsolidatedBriefingScript":
    """
    Create a new ConsolidatedBriefingScript with lines grouped into speaker segments
    optimized for multi-speaker TTS generation.

    This method groups consecutive lines by speaker combinations (1-2 speakers max)
    to minimize API calls while respecting Gemini's multi-speaker TTS limits.
    The first speaker always starts as a solo segment.

    Returns:
        ConsolidatedBriefingScript: New script with speaker segments for efficient TTS
    """
    logger = structlog.get_logger()

    original_lines = self.lines
    total_original_lines = len(original_lines)

    logger.debug("Starting speaker segment consolidation", total_lines=total_original_lines)

    if not original_lines:
      logger.debug("No lines to consolidate, returning empty script")
      return ConsolidatedBriefingScript(segments=[])

    segments: list[SpeakerSegment] = []
    current_segment_lines: list[ScriptLine] = []
    current_speakers: set[str] = set()
    is_first_segment = True

    def finalize_current_segment():
      """Helper to finalize the current segment and add it to segments."""
      if not current_segment_lines:
        return

      # Determine character assignments and style directions
      speakers_list = sorted(list(current_speakers))  # Sort for consistent ordering
      character_1_slug = speakers_list[0]

      # Find the style direction for character 1 (use first occurrence)
      character_1_style_direction = None
      for line in current_segment_lines:
        if line.character_slug == character_1_slug:
          character_1_style_direction = line.character_style_direction
          break

      # Handle second character if present (ensure speaker1 != speaker2)
      character_2_slug = None
      character_2_style_direction = None
      if len(speakers_list) > 1:
        character_2_slug = speakers_list[1]
        # Ensure speaker1 != speaker2
        assert character_1_slug != character_2_slug, (
          f"Speaker 1 and 2 cannot be the same: {character_1_slug}"
        )

        # Find the style direction for character 2 (use first occurrence)
        for line in current_segment_lines:
          if line.character_slug == character_2_slug:
            character_2_style_direction = line.character_style_direction
            break

      segment = SpeakerSegment(
        lines=current_segment_lines.copy(),
        character_1_slug=character_1_slug,
        character_1_style_direction=character_1_style_direction,
        character_2_slug=character_2_slug,
        character_2_style_direction=character_2_style_direction,
      )

      segments.append(segment)
      logger.debug(
        "Created speaker segment",
        speakers=len(current_speakers),
        lines=len(current_segment_lines),
        character_1=character_1_slug,
        character_2=character_2_slug,
      )

    for line in original_lines:
      line_speaker = {line.character_slug}

      # For the first segment, always start as solo
      if is_first_segment:
        current_segment_lines = [line]
        current_speakers = line_speaker
        is_first_segment = False
        continue

      # Check if we can add this line to the current segment
      potential_speakers = current_speakers | line_speaker

      if len(potential_speakers) <= 2:
        # We can add this line to the current segment
        current_segment_lines.append(line)
        current_speakers = potential_speakers
      else:
        # We need to start a new segment (would exceed 2 speakers)
        finalize_current_segment()

        # Start new segment with this line
        current_segment_lines = [line]
        current_speakers = line_speaker

    # Don't forget the last segment
    finalize_current_segment()

    total_segments = len(segments)
    total_segment_lines = sum(len(segment.lines) for segment in segments)
    consolidation_ratio = total_segments / total_original_lines if total_original_lines > 0 else 0

    logger.debug(
      "Speaker segment consolidation completed",
      original_lines=total_original_lines,
      segments=total_segments,
      total_segment_lines=total_segment_lines,
      consolidation_ratio=round(consolidation_ratio, 3),
    )

    return ConsolidatedBriefingScript(segments=segments)


class ConsolidatedBriefingScript(BaseModel):
  """
  A briefing script consolidated into speaker segments for optimized TTS generation.

  This represents the script after consolidation, where consecutive lines have been
  grouped into segments of 1-2 speakers to minimize API calls while respecting
  the multi-speaker TTS API limits.
  """

  segments: list[SpeakerSegment] = Field(..., description="Ordered list of speaker segments")

  @property
  def lines(self) -> list[ScriptLine]:
    """
    Flatten all segments into a single list of script lines for compatibility.
    """
    return [line for segment in self.segments for line in segment.lines]

  def get_all_characters(self) -> set[str]:
    """Extract all unique character slugs used in the consolidated script."""
    return {line.character_slug for segment in self.segments for line in segment.lines}
