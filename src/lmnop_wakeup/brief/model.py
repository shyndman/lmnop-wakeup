from io import StringIO

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
