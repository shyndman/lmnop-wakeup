import datetime
import mimetypes
from pathlib import Path
from typing import Any, cast

import eyed3
import eyed3.id3
import structlog
from eyed3.core import AudioFile
from eyed3.id3 import Genre, Tag
from eyed3.id3.tag import CommentsAccessor, ImagesAccessor, UserTextsAccessor
from pydantic import BaseModel, Field

from lmnop_wakeup.brief.model import ConsolidatedBriefingScript
from lmnop_wakeup.core.date import get_ordinal_suffix

logger = structlog.get_logger(__name__)


class BriefingID3Tags(BaseModel):
  """Model for ID3 tag data for a briefing audio file."""

  title: str = Field(
    ..., description="Episode title (e.g., 'The Morning Briefing: July 3rd, 2025')"
  )
  artist: str = Field(default="lmnop", description="Podcast author")
  album: str = Field(default="Daily Briefings", description="Podcast series name")
  album_artist: str = Field(default="lmnop", description="Album artist")
  release_date: datetime.date = Field(..., description="Date of the briefing")
  genre: str = Field(default="Podcast", description="Podcast genre")
  year: int = Field(..., description="Year of release")
  comment: str = Field(..., description="Full script in markdown format")
  publisher: str = Field(default="LMNOP Wake Up", description="Publisher information")

  @classmethod
  def from_briefing_data(
    cls,
    briefing_date: datetime.date,
    script: ConsolidatedBriefingScript,
    location_name: str | None = None,
  ) -> "BriefingID3Tags":
    """Create ID3 tags from briefing data."""
    # Format the date nicely for the title
    day_with_suffix = f"{briefing_date.day}{get_ordinal_suffix(briefing_date.day)}"
    formatted_date = briefing_date.strftime(f"%B {day_with_suffix}, %Y")

    # Create title
    title = f"The Morning Briefing: {formatted_date}"

    # Convert script to markdown format
    comment = _format_script_as_markdown(script)

    return cls(
      title=title,
      release_date=briefing_date,
      year=briefing_date.year,
      comment=comment,
    )


def _format_script_as_markdown(script: ConsolidatedBriefingScript) -> str:
  """Format a briefing script as markdown with speaker names."""
  lines = []

  for segment in script.segments:
    # Format each line in the segment
    for line in segment.lines:
      # Use title case of character slug as the display name
      character_name = line.character_slug.replace("_", " ").title()
      lines.append(f"**{character_name}**: {line.text}")

    # Add blank line between segments
    lines.append("")

  return "\n".join(lines).strip()


class ID3Tagger:
  """Handles adding ID3 tags to MP3 files."""

  def add_tags_to_file(
    self, mp3_path: Path, tags: BriefingID3Tags, cover_image_path: Path | None = None
  ) -> None:
    """Add ID3 tags to an MP3 file."""
    if not mp3_path.exists():
      raise FileNotFoundError(f"MP3 file not found: {mp3_path}")

    if not str(mp3_path).lower().endswith(".mp3"):
      raise ValueError(f"File must be an MP3: {mp3_path}")

    logger.info(f"Adding ID3 tags to {mp3_path}")
    logger.debug(
      "Tag values to write",
      title=tags.title,
      artist=tags.artist,
      album=tags.album,
      genre=tags.genre,
      release_date=tags.release_date,
      comment_length=len(tags.comment),
    )

    # Load the MP3 file
    audiofile: AudioFile | None = eyed3.load(str(mp3_path))
    if audiofile is None:
      raise ValueError(f"Failed to load MP3 file: {mp3_path}")

    # Initialize tag if it doesn't exist
    if audiofile.tag is None:
      audiofile.initTag()

    # Set all the tags
    tag = cast(Tag, audiofile.tag)
    tag.title = tags.title
    tag.artist = tags.artist
    tag.album = tags.album
    tag.album_artist = tags.album_artist
    tag.genre = tags.genre
    # Convert datetime.date to string format that eyeD3 accepts
    release_date_string = tags.release_date.strftime("%Y-%m-%d")
    recording_date_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tag.recording_date = recording_date_string
    tag.release_date = release_date_string
    tag.original_release_date = release_date_string

    logger.debug(
      "Date tags",
      recording_date=recording_date_string,
      release_date=release_date_string,
    )

    # Add comment (full script)
    cast(CommentsAccessor, tag.comments).set(tags.comment)

    # Add publisher using built-in property
    tag.publisher = tags.publisher

    # Add podcast-specific tags
    user_text_frames = cast(UserTextsAccessor, tag.user_text_frames)
    user_text_frames.set("PODCAST", "1")
    user_text_frames.set("PODCASTURL", "https://github.com/shyndman/lmnop_wakeup")

    # Add cover art if provided
    if cover_image_path and cover_image_path.exists():
      # Detect MIME type
      mime_type, _ = mimetypes.guess_type(str(cover_image_path))
      if mime_type is None:
        mime_type = "image/png"  # Default fallback

      logger.debug(
        "Adding cover image",
        path=cover_image_path,
        size=cover_image_path.stat().st_size,
        mime_type=mime_type,
      )

      with open(cover_image_path, "rb") as img_file:
        img_data = img_file.read()

        # Remove the problematic conditional check
        cast(ImagesAccessor, tag.images).set(
          type_=3,  # Front cover
          img_data=img_data,
          mime_type=mime_type,
          description="Podcast Cover",
        )

        logger.debug("Cover image data added to tag")
    else:
      logger.warning(
        "No cover image to add",
        cover_image_path=cover_image_path,
        exists=cover_image_path.exists() if cover_image_path else False,
      )

    # Save the tags
    tag.save(version=eyed3.id3.ID3_V2_4)

    logger.info(f"Successfully saved ID3 tags to {mp3_path}")

    # Verify and log what was actually written
    try:
      written_tags = self.read_tags_from_file(mp3_path)
      logger.info(
        "ID3 tags verification",
        mp3_path=mp3_path,
        title=written_tags.get("title"),
        artist=written_tags.get("artist"),
        album=written_tags.get("album"),
        genre=written_tags.get("genre"),
        release_date=written_tags.get("release_date"),
        has_cover_art=written_tags.get("has_cover_art"),
        publisher=written_tags.get("publisher"),
      )
    except Exception as e:
      logger.warning(f"Failed to verify written tags: {e}")

  def read_tags_from_file(self, mp3_path: Path) -> dict[str, Any]:
    """Read ID3 tags from an MP3 file for verification."""
    if not mp3_path.exists():
      raise FileNotFoundError(f"MP3 file not found: {mp3_path}")

    audiofile: AudioFile | None = eyed3.load(str(mp3_path))
    if audiofile is None or audiofile.tag is None:
      return {}

    tag = cast(Tag, audiofile.tag)
    genre = cast(Genre | None, tag.genre)
    comments = tag.comments or []
    images = tag.images or []
    return {
      "title": tag.title,
      "artist": tag.artist,
      "album": tag.album,
      "album_artist": tag.album_artist,
      "genre": genre.name if genre else None,
      "release_date": str(tag.release_date) if tag.release_date else None,
      "comments": [str(c) for c in comments],
      "publisher": tag.publisher,
      "has_cover_art": len(images) > 0,
    }
