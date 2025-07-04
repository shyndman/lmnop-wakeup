import datetime
import tempfile
from pathlib import Path

import pytest
from pydub import AudioSegment

from lmnop_wakeup.audio.id3_tags import BriefingID3Tags, ID3Tagger
from lmnop_wakeup.brief.model import (
  ConsolidatedBriefingScript,
  ScriptLine,
  SpeakerSegment,
)


@pytest.fixture
def sample_script():
  """Create a sample briefing script for testing."""
  segments = [
    SpeakerSegment(
      lines=[
        ScriptLine(
          character_slug="sarah",
          text="Good morning! It's a beautiful Thursday.",
          character_style_direction="sound professionally efficient with a brisk pace",
          is_introduction=True,
        )
      ],
      character_1_slug="sarah",
      character_1_style_direction="sound professionally efficient with a brisk pace",
      is_introduction=True,
    ),
    SpeakerSegment(
      lines=[
        ScriptLine(
          character_slug="marcus",
          text="Indeed it is, Sarah. Today's weather looks fantastic.",
          character_style_direction="sound thoughtful and analytical",
        ),
        ScriptLine(
          character_slug="sarah",
          text="Let's dive into your schedule for the day.",
          character_style_direction="sound upbeat and energetic",
        ),
      ],
      character_1_slug="marcus",
      character_1_style_direction="sound thoughtful and analytical",
      character_2_slug="sarah",
      character_2_style_direction="sound upbeat and energetic",
      is_introduction=False,
    ),
  ]

  return ConsolidatedBriefingScript(
    segments=segments,
  )


@pytest.fixture
def sample_mp3_file():
  """Create a temporary MP3 file for testing."""
  with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
    # Create a silent audio segment and export as MP3
    silent = AudioSegment.silent(duration=1000)  # 1 second
    silent.export(tmp.name, format="mp3")
    return Path(tmp.name)


def test_briefing_id3_tags_from_briefing_data(sample_script):
  """Test creating ID3 tags from briefing data."""
  briefing_date = datetime.date(2025, 7, 3)

  tags = BriefingID3Tags.from_briefing_data(
    briefing_date=briefing_date,
    script=sample_script,
    location_name="San Francisco",
  )

  assert tags.title == "The Morning Briefing: July 3rd, 2025"
  assert tags.artist == "lmnop"
  assert tags.album == "Daily Briefings"
  assert tags.release_date == briefing_date
  assert tags.year == 2025
  assert tags.genre == "News & Politics"
  assert tags.publisher == "LMNOP Wake Up"

  # Check the markdown formatted comment
  assert "**Sarah**:" in tags.comment
  assert "**Marcus**:" in tags.comment
  assert "Good morning! It's a beautiful Thursday." in tags.comment
  assert "Indeed it is, Sarah. Today's weather looks fantastic." in tags.comment


def test_id3_tagger_add_tags(sample_mp3_file, sample_script):
  """Test adding ID3 tags to an MP3 file."""
  briefing_date = datetime.date(2025, 7, 3)
  tags = BriefingID3Tags.from_briefing_data(briefing_date, sample_script)

  tagger = ID3Tagger()
  tagger.add_tags_to_file(sample_mp3_file, tags)

  # Read back the tags
  read_tags = tagger.read_tags_from_file(sample_mp3_file)

  assert read_tags["title"] == "The Morning Briefing: July 3rd, 2025"
  assert read_tags["artist"] == "lmnop"
  assert read_tags["album"] == "Daily Briefings"
  assert read_tags["genre"] == "News & Politics"
  assert "2025" in read_tags["release_date"]
  assert len(read_tags["comments"]) > 0
  assert read_tags["publisher"] == "LMNOP Wake Up"

  # Clean up
  sample_mp3_file.unlink()


def test_id3_tagger_file_not_found():
  """Test handling of non-existent file."""
  tagger = ID3Tagger()
  tags = BriefingID3Tags(
    title="Test",
    release_date=datetime.date.today(),
    year=2025,
    comment="Test comment",
  )

  with pytest.raises(FileNotFoundError):
    tagger.add_tags_to_file(Path("/nonexistent/file.mp3"), tags)


def test_id3_tagger_invalid_file_type():
  """Test handling of non-MP3 file."""
  with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
    tmp.write(b"Not an MP3 file")
    tmp_path = Path(tmp.name)

  tagger = ID3Tagger()
  tags = BriefingID3Tags(
    title="Test",
    release_date=datetime.date.today(),
    year=2025,
    comment="Test comment",
  )

  with pytest.raises(ValueError, match="File must be an MP3"):
    tagger.add_tags_to_file(tmp_path, tags)

  # Clean up
  tmp_path.unlink()
