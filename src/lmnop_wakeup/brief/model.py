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

  def consolidate_dialogue(self) -> "BriefingScript":
    """
    Create a new BriefingScript with consecutive lines merged when they have
    the same character and style direction.

    This method produces a single "Merged" section containing all script lines,
    with consecutive lines from the same character with identical style directions
    combined into single lines with concatenated text.

    Returns:
        BriefingScript: New script with merged lines in a single section
    """
    logger = structlog.get_logger()

    original_lines = self.lines
    total_original_lines = len(original_lines)

    logger.debug("Starting line merge operation", total_lines=total_original_lines)

    if not original_lines:
      logger.debug("No lines to merge, returning empty script")
      return BriefingScript(sections=[ScriptSection(name="Merged", lines=[])])

    merged_lines: list[ScriptLine] = []
    current_merged_line: ScriptLine | None = None
    merge_operations = 0

    for line in original_lines:
      if (
        current_merged_line
        and current_merged_line.character_slug == line.character_slug
        and current_merged_line.character_style_direction == line.character_style_direction
      ):
        # Merge with current line
        current_merged_line.text += " " + line.text
        merge_operations += 1

        logger.debug(
          "Merged lines",
          character=line.character_slug,
          style_direction=line.character_style_direction[:50] + "..."
          if len(line.character_style_direction) > 50
          else line.character_style_direction,
          merged_text_length=len(current_merged_line.text),
        )
      else:
        # Start new merged line
        if current_merged_line:
          merged_lines.append(current_merged_line)

        # Create a copy of the line to avoid mutating the original
        current_merged_line = ScriptLine(
          character_slug=line.character_slug,
          character_style_direction=line.character_style_direction,
          text=line.text,
        )

    # Don't forget the last line
    if current_merged_line:
      merged_lines.append(current_merged_line)

    total_merged_lines = len(merged_lines)
    merge_ratio = (
      (total_original_lines - total_merged_lines) / total_original_lines
      if total_original_lines > 0
      else 0
    )

    logger.debug(
      "Line merge completed",
      original_lines=total_original_lines,
      merged_lines=total_merged_lines,
      merge_operations=merge_operations,
      merge_ratio=round(merge_ratio, 3),
    )

    return BriefingScript(sections=[ScriptSection(name="Merged", lines=merged_lines)])
