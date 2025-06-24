"""Shared utilities for CLI commands."""

import structlog
from rich.console import Console

from ..core.terminal import is_interactive_terminal

logger = structlog.get_logger()


def should_prompt_user() -> bool:
  """Check if we should prompt the user for interactive input.

  Returns True if we're in an interactive terminal, False otherwise.
  This is used as the default for human-in-the-loop workflow steps.
  """
  return is_interactive_terminal()


def get_console() -> Console:
  """Get a Rich console instance."""
  return Console()
