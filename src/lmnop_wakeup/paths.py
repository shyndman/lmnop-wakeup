import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from importlib import resources
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import APP_DIRS

if TYPE_CHECKING:
  from .brief.model import BriefingScript


def get_data_path() -> Path:
  """Get the data directory path, checking DATA_PATH env var first."""
  data_path_env = os.getenv("DATA_PATH")
  if data_path_env:
    return Path(data_path_env)
  return APP_DIRS.user_state_path


def get_theme_music_path() -> Path:
  """Get the path to the looping theme music resource file."""
  # First check if a custom theme music path is set via environment variable
  theme_music_env = os.getenv("THEME_MUSIC_PATH")
  if theme_music_env:
    return Path(theme_music_env)

  # Default to a resource file in the audio module
  import lmnop_wakeup.audio

  audio_files = files(lmnop_wakeup.audio)
  theme_file = audio_files / "theme.mp3"

  with resources.as_file(theme_file) as theme_file:
    return theme_file


def get_theme_intro_path() -> Path:
  """Get the path to the theme intro music resource file."""
  # First check if a custom theme intro path is set via environment variable
  theme_intro_env = os.getenv("THEME_INTRO_PATH")
  if theme_intro_env:
    return Path(theme_intro_env)

  # Default to a resource file in the audio module
  import lmnop_wakeup.audio

  audio_files = files(lmnop_wakeup.audio)
  theme_intro_file = audio_files / "theme_intro.mp3"

  with resources.as_file(theme_intro_file) as theme_intro_file:
    return theme_intro_file


@dataclass
class BriefingDirectory:
  briefing_date: date
  base_path: Path

  @classmethod
  def for_date(cls, briefing_date: date, data_path: Path | None = None) -> "BriefingDirectory":
    """Create BriefingDirectory for specific date."""
    base = data_path or get_data_path()
    return cls(briefing_date=briefing_date, base_path=base / briefing_date.isoformat())

  # File path properties
  @property
  def brief_json_path(self) -> Path:
    return self.base_path / "brief.json"

  @property
  def consolidated_brief_json_path(self) -> Path:
    return self.base_path / "consolidated_brief.json"

  @property
  def workflow_state_path(self) -> Path:
    return self.base_path / "workflow_state.json"

  @property
  def briefing_audio_path(self) -> Path:
    """Path to intermediate briefing audio file (before theme music)."""
    return self.base_path / "briefing.mp3"

  @property
  def master_audio_path(self) -> Path:
    """Path to final master audio file (with theme music)."""
    return self.base_path / "master_briefing.mp3"

  @property
  def wav_files(self) -> list[Path]:
    """Get all WAV files sorted by numeric filename."""
    if not self.base_path.exists():
      return []
    wav_files = list(self.base_path.glob("*.wav"))
    wav_files.sort(key=lambda f: int(f.stem))
    return wav_files

  # Validation methods
  def exists(self) -> bool:
    return self.base_path.exists() and self.base_path.is_dir()

  def has_brief_json(self) -> bool:
    return self.brief_json_path.exists()

  def has_workflow_state(self) -> bool:
    return self.workflow_state_path.exists()

  def has_master_audio(self) -> bool:
    return self.master_audio_path.exists()

  def is_complete(self) -> bool:
    """Check if directory contains all expected files."""
    return (
      self.exists()
      and self.has_brief_json()
      and self.has_workflow_state()
      and self.has_master_audio()
    )

  # Content loading
  def load_script(self) -> "BriefingScript":
    """Load briefing script from brief.json."""
    from .brief.model import BriefingScript

    if not self.has_brief_json():
      raise FileNotFoundError(f"No briefing script found for {self.briefing_date}")
    content = self.brief_json_path.read_text()
    return BriefingScript.model_validate_json(content)

  def load_workflow_state(self) -> dict[str, Any]:
    """Load workflow state from workflow_state.json."""
    if not self.has_workflow_state():
      raise FileNotFoundError(f"No workflow state found for {self.briefing_date}")
    return json.loads(self.workflow_state_path.read_text())

  # Directory management
  def ensure_exists(self) -> None:
    """Create directory if it doesn't exist."""
    self.base_path.mkdir(parents=True, exist_ok=True)


class BriefingDirectoryCollection:
  def __init__(self, data_path: Path | None = None):
    self.data_path = data_path or get_data_path()

  def discover_all(self) -> list[BriefingDirectory]:
    """Find all briefing directories, sorted by date descending."""
    briefing_dirs = []

    if not self.data_path.exists():
      return briefing_dirs

    for item in self.data_path.iterdir():
      if item.is_dir():
        try:
          # Parse ISO date format (YYYY-MM-DD)
          briefing_date = date.fromisoformat(item.name)
          briefing_dirs.append(BriefingDirectory(briefing_date, item))
        except ValueError:
          # Skip directories that aren't valid dates
          continue

    # Sort by date descending (newest first)
    briefing_dirs.sort(key=lambda bd: bd.briefing_date, reverse=True)
    return briefing_dirs

  def __iter__(self) -> Iterator[BriefingDirectory]:
    """Iterate over briefing directories in descending date order."""
    return iter(self.discover_all())

  def get_latest(self, count: int = 1) -> list[BriefingDirectory]:
    """Get the most recent N briefing directories."""
    return self.discover_all()[:count]

  def get_for_date(self, briefing_date: date) -> BriefingDirectory:
    """Get briefing directory for specific date (creates instance even if doesn't exist)."""
    return BriefingDirectory.for_date(briefing_date, self.data_path)

  def get_existing_for_date(self, briefing_date: date) -> BriefingDirectory | None:
    """Get briefing directory for specific date only if it exists."""
    bd = self.get_for_date(briefing_date)
    return bd if bd.exists() else None
