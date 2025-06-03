from io import StringIO
from typing import Self

from pydantic import BaseModel, Field, model_validator

from lmnop_wakeup.core.typing import assert_not_none


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
    ScriptLine(character_slug="sarah", text="Well folks, it's looking like a beautiful day ahead!")
    ScriptLine(character_slug="marcus", text="Hold on Sarah, have you seen the storm brewing?")
  """

  character_slug: str = Field(..., description="Character identifier from the character pool")
  text: str = Field(..., description="Dialogue text maintaining character voice", min_length=1)


class TonalDialogueGroup(BaseModel):
  """
  A group of dialogue lines that share the same emotional tone and style direction.

  This grouping is critical for efficient API usage with the multi-speaker synthesis API. All lines
  within this group will be processed together with the same stylistic instructions, minimizing the
  number of API calls needed.

  The emotional/style directions should be rich and descriptive to guide the voice synthesis
  effectively. Think "sarcastically enthusiastic, at a playful pace" rather than just "sarcastic".

  Examples:
    - A weather discussion with upbeat, cheerful energy
    - A traffic report delivered with urgent concern
    - Casual banter with relaxed, friendly tones
  """

  character_1_slug: str = Field(
    ..., description="First character participating in this tonal group"
  )
  character_1_style_direction: str = Field(
    ..., description="Detailed emotional and stylistic direction for character_1", min_length=15
  )
  character_2_slug: str | None = Field(
    None,
    description="Second character participating in this tonal group. Set to be None if there "
    "is only one speaker in the tonal group.",
  )
  character_2_style_direction: str | None = Field(
    None,
    description="Detailed emotional and stylistic direction for character_2. Set to be None if "
    "there is only one speaker in the tonal group.",
    min_length=15,
  )
  lines: list[ScriptLine] = Field(
    ..., description="All dialogue lines that share this emotional tone", min_length=1
  )

  @property
  def character_slugs(self) -> set[str]:
    return {line.character_slug for line in self.lines}

  @property
  def character_count(self) -> int:
    return len(self.character_slugs)

  @property
  def is_single_speaker(self):
    """Check if a dialogue group has only one speaker."""
    return self.character_2_slug is None

  def remove_unused_character_direction(self):
    slugs = self.character_slugs
    if self.character_1_slug in slugs and self.character_2_slug in slugs:
      return

    expecting_use_of_2 = False
    if self.character_1_slug not in slugs:
      self.character_1_slug = assert_not_none(self.character_2_slug)
      self.character_1_style_direction = assert_not_none(self.character_2_style_direction)
      expecting_use_of_2 = True

    if (self.character_2_slug in slugs) != expecting_use_of_2:
      if expecting_use_of_2:
        raise ValueError("Expected character_2_slug to be used, but it was not found in lines.")
      else:
        raise ValueError(
          "Expected character_2_slug to be unused, but it was found in lines.\n"
          f"{self.build_prompt()}"
        )

    self.character_2_slug = None
    self.character_2_style_direction = None

  @model_validator(mode="after")
  def validate_characters_in_lines(self) -> "TonalDialogueGroup":
    """Ensure all lines use only the two specified characters."""
    valid_characters = {self.character_1_slug, self.character_2_slug}
    for line in self.lines:
      if line.character_slug not in valid_characters:
        raise ValueError(
          f"Line character '{line.character_slug}' not in group characters {valid_characters}"
        )
    return self

  def build_prompt(self) -> str:
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

  @model_validator(mode="after")
  def _validate_unique(self) -> Self:  # noqa: F821
    if self.character_1_slug == self.character_2_slug:
      raise ValueError(
        "Both characters in a tonal group cannot be the same. "
        "Please ensure character_1_slug and character_2_slug are distinct, either by "
        "introducing a character, or setting character_2_slug to None"
      )
    return self


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
  dialogue_groups: list[TonalDialogueGroup] = Field(
    ..., description="Ordered list of dialogue groups within this section", min_length=1
  )

  def normalize_doubled_speaker(self):
    for group in self.dialogue_groups:
      if group.character_1_slug == group.character_2_slug:
        # If both characters are the same, remove character_2
        group.character_2_slug = None
        group.character_2_style_direction = None

  def merge_single_speakers(self):
    """
    Merges consecutive single-speaker dialogue groups within each section.

    When two consecutive dialogue groups each have only one speaker, this function
    merges them by adding the second group's speaker as character_2 in the first
    group and appending the second group's lines to the first group.

    Args:
      data: JSON dictionary containing sections with dialogue_groups

    Returns:
      Modified data dictionary with merged single-speaker groups
    """
    groups = self.dialogue_groups
    i = 0
    while i < len(groups) - 1:
      current_group = groups[i]
      next_group = groups[i + 1]

      # Check if both are single-speaker groups
      if current_group.is_single_speaker and next_group.is_single_speaker:
        # Merge next_group into current_group
        current_group.character_2_slug = next_group.character_1_slug
        current_group.character_2_style_direction = next_group.character_1_style_direction
        current_group.lines.extend(next_group.lines)

        # Remove the next_group from the list
        groups.pop(i + 1)

      # Always increment i
      i += 1


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
    characters = set()
    for section in self.sections:
      for group in section.dialogue_groups:
        characters.add(group.character_1_slug)
        characters.add(group.character_2_slug)
    return characters

  def dialogue_groups(self):
    for section in self.sections:
      for group in section.dialogue_groups:
        yield group

  def _merge_single_character_groups(
    self, group1: TonalDialogueGroup, group2: TonalDialogueGroup
  ) -> TonalDialogueGroup:
    """Merge two single-character dialogue groups into one two-character group."""
    return group1.model_copy(
      update={
        "character_2_slug": group2.character_1_slug,
        "character_2_style_direction": group2.character_1_style_direction,
        "lines": group1.lines + group2.lines,
      }
    )

  def clean_script(self) -> "BriefingScript":
    """Clean the script by removing unused character directions and merging single-character
    groups."""
    copy = self.model_copy()

    for section in copy.sections:
      # First, clean unused character directions in all groups
      for group in section.dialogue_groups:
        group.remove_unused_character_direction()

      # Then merge consecutive single-character groups
      section.merge_single_speakers()

    return copy
