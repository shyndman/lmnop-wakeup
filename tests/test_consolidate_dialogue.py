"""
Test for the consolidate_dialogue method in BriefingScript
"""

from lmnop_wakeup.brief.model import BriefingScript, ScriptLine, ScriptSection


def test_consolidate_dialogue():
  """Test that consolidate_dialogue properly merges consecutive lines from same character with
  same style."""
  # Create a test script with mergeable lines
  script = BriefingScript(
    sections=[
      ScriptSection(
        name="Weather",
        lines=[
          ScriptLine(
            character_slug="sarah",
            character_style_direction="cheerful and energetic",
            text="Good morning everyone!",
          ),
          ScriptLine(
            character_slug="sarah",
            character_style_direction="cheerful and energetic",
            text="It's a beautiful day today.",
          ),
          ScriptLine(
            character_slug="marcus",
            character_style_direction="serious and concerned",
            text="But there's rain coming later.",
          ),
          ScriptLine(
            character_slug="marcus",
            character_style_direction="serious and concerned",
            text="You should bring an umbrella.",
          ),
        ],
      ),
      ScriptSection(
        name="Traffic",
        lines=[
          ScriptLine(
            character_slug="sarah",
            character_style_direction="cheerful and energetic",
            text="Traffic is light this morning!",
          )
        ],
      ),
    ]
  )

  # Test the consolidation
  merged_script = script.consolidate_dialogue()

  # Verify structure
  assert len(merged_script.sections) == 1
  assert merged_script.sections[0].name == "Merged"

  # Should have 3 lines (2 merged sarah lines + 1 merged marcus line + 1 final sarah line)
  assert len(merged_script.lines) == 3

  # Check first merged line (sarah's two consecutive lines)
  first_line = merged_script.lines[0]
  assert first_line.character_slug == "sarah"
  assert first_line.character_style_direction == "cheerful and energetic"
  assert first_line.text == "Good morning everyone! It's a beautiful day today."

  # Check second merged line (marcus's two consecutive lines)
  second_line = merged_script.lines[1]
  assert second_line.character_slug == "marcus"
  assert second_line.character_style_direction == "serious and concerned"
  assert second_line.text == "But there's rain coming later. You should bring an umbrella."

  # Check third line (sarah's single line from Traffic section)
  third_line = merged_script.lines[2]
  assert third_line.character_slug == "sarah"
  assert third_line.character_style_direction == "cheerful and energetic"
  assert third_line.text == "Traffic is light this morning!"


def test_consolidate_dialogue_no_merging():
  """Test that consolidate_dialogue works when no merging is possible."""
  script = BriefingScript(
    sections=[
      ScriptSection(
        name="Test",
        lines=[
          ScriptLine(
            character_slug="sarah",
            character_style_direction="cheerful and energetic",
            text="Hello!",
          ),
          ScriptLine(
            character_slug="marcus",
            character_style_direction="serious and concerned",
            text="Goodbye!",
          ),
        ],
      )
    ]
  )

  merged_script = script.consolidate_dialogue()

  # Should still create single "Merged" section
  assert len(merged_script.sections) == 1
  assert merged_script.sections[0].name == "Merged"

  # Should have same number of lines since no merging occurred
  assert len(merged_script.lines) == 2
  assert merged_script.lines[0].text == "Hello!"
  assert merged_script.lines[1].text == "Goodbye!"


def test_consolidate_dialogue_empty_section():
  """Test that consolidate_dialogue handles sections with no lines."""
  script = BriefingScript(
    sections=[
      ScriptSection(
        name="Empty",
        lines=[
          ScriptLine(
            character_slug="sarah",
            character_style_direction="neutral and informative",
            text="Just one line.",
          )
        ],
      )
    ]
  )

  merged_script = script.consolidate_dialogue()

  assert len(merged_script.sections) == 1
  assert merged_script.sections[0].name == "Merged"
  assert len(merged_script.lines) == 1
  assert merged_script.lines[0].text == "Just one line."
