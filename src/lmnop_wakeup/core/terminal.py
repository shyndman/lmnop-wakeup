import sys


def is_interactive_terminal() -> bool:
  """Check if we're running in an interactive terminal."""
  return sys.stdin.isatty() and sys.stdout.isatty()
