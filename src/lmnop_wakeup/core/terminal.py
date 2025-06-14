import sys
from pathlib import Path


def is_interactive_terminal() -> bool:
  """Check if we're running in an interactive terminal."""
  return sys.stdin.isatty() and sys.stdout.isatty()


def hyperlink(url: str, text: str) -> str:
  """Create a terminal hyperlink if TTY supports it."""
  if sys.stdout.isatty():
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
  return text


def file_hyperlink(path: Path | str) -> str:
  """Create a file:// hyperlink for a path if TTY supports it."""
  path_obj = Path(path)
  file_url = path_obj.absolute().as_uri()
  return hyperlink(file_url, str(path))
