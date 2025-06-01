from io import StringIO

from pydantic import BaseModel, Field, computed_field, model_validator

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
    ...,
    description="Second character participating in this tonal group. Can be null if there "
    "is only one speaker in the tonal group.",
  )
  character_2_style_direction: str | None = Field(
    ...,
    description="Detailed emotional and stylistic direction for character_2. Can be null if "
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

  def remove_unused_character_direction(self):
    if self.character_count > 1:
      return

    slugs = self.character_slugs
    expecting_use_of_2 = False
    if self.character_1_slug not in slugs:
      self.character_1_slug = assert_not_none(self.character_2_slug)
      self.character_1_style_direction = assert_not_none(self.character_2_style_direction)
      expecting_use_of_2 = True

    if (self.character_2_slug in slugs) != expecting_use_of_2:
      if expecting_use_of_2:
        raise ValueError("Expected character_2_slug to be used, but it was not found in lines.")
      else:
        raise ValueError("Expected character_2_slug to be unused, but it was found in lines.")

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
  character_count: int = Field(
    ..., description="Total number of unique characters used in this script", ge=4, le=6
  )

  @computed_field
  @property
  def estimated_duration_minutes(self) -> float:
    """Estimate duration based on total word count and average speaking pace."""
    total_words = sum(
      len(line.text.split())
      for section in self.sections
      for group in section.dialogue_groups
      for line in group.lines
    )
    return total_words / 150

  def get_all_characters(self) -> set[str]:
    """Extract all unique character slugs used in the script."""
    characters = set()
    for section in self.sections:
      for group in section.dialogue_groups:
        characters.add(group.character_1_slug)
        characters.add(group.character_2_slug)
    return characters

  @model_validator(mode="after")
  def validate_character_consistency(self) -> "BriefingScript":
    """Ensure character count matches actual character usage."""
    actual_count = len(self.get_all_characters())
    if actual_count != self.character_count:
      raise ValueError(
        f"Character count mismatch: declared {self.character_count}, actual {actual_count}"
      )
    return self

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

  def _merge_consecutive_single_character_groups(
    self, groups: list[TonalDialogueGroup]
  ) -> list[TonalDialogueGroup]:
    """Merge consecutive single-character groups to optimize API calls."""
    if len(groups) <= 1:
      return groups

    merged_groups = []
    i = 0

    while i < len(groups):
      current_group = groups[i]

      # Check if we can merge with the next group
      if (
        i + 1 < len(groups)
        and current_group.character_count == 1
        and groups[i + 1].character_count == 1
      ):
        # Merge the two single-character groups
        merged_group = self._merge_single_character_groups(current_group, groups[i + 1])
        merged_groups.append(merged_group)
        i += 2  # Skip the next group since we merged it
      else:
        # Can't merge, just add the current group
        merged_groups.append(current_group)
        i += 1

    return merged_groups

  def clean_script(self) -> "BriefingScript":
    """Clean the script by removing unused character directions and merging single-character
    groups."""
    copy = self.model_copy()

    for section in copy.sections:
      # First, clean unused character directions in all groups
      for group in section.dialogue_groups:
        group.remove_unused_character_direction()

      # Then merge consecutive single-character groups
      section.dialogue_groups = self._merge_consecutive_single_character_groups(
        section.dialogue_groups
      )

    return copy
