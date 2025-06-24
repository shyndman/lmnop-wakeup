"""CLI commands for briefing generation and data management."""

from datetime import date
from typing import override

import clypi
import structlog
from clypi import Command, arg
from rich.console import Console

from ..arg import parse_location
from ..core.cache import get_cache
from ..core.terminal import file_hyperlink
from ..env import assert_env
from ..location.model import CoordinateLocation, LocationName, location_named
from ..paths import BriefingDirectory
from .shared import should_prompt_user

logger = structlog.get_logger()


class Script(Command):
  """Generates a daily briefing for the users based on location and date"""

  current_location: CoordinateLocation = arg(
    location_named(LocationName.home),
    parser=parse_location,
    help="name or latlng of the user's location",
  )
  briefing_date: date = arg(inherited=True)
  yes: bool = arg(
    default=False, short="y", help="skip all interactive prompts and auto-approve workflow steps"
  )
  thread_id: str | None = arg(
    default=None,
    help="thread ID to continue existing workflow (if not provided, continues most recent "
    "incomplete thread)",
  )

  @override
  async def run(self):
    from ..workflow import WorkflowAbortedByUser, run_workflow

    async with get_cache():
      assert_env()

      # Determine if we should use interactive mode
      interactive = should_prompt_user() and not self.yes

      try:
        briefing_script, _state = await run_workflow(
          briefing_date=self.briefing_date,
          briefing_location=self.current_location,
          thread_id=self.thread_id,
          interactive=interactive,
        )
      except WorkflowAbortedByUser as e:
        logger.info(f"Workflow aborted: {e.message}")
        print(f"\n[yellow]{e.message}[/yellow]")
        print("You can resume this workflow later using the same thread ID.")
        return

      if briefing_script is None:
        return

      console = Console()

      # Use the new display format with Rich markup
      display_text = briefing_script.build_display_text()
      console.print(clypi.boxed(display_text, width=80, align="left"))
      print("")

      # Log paths to generated files
      briefing_dir = BriefingDirectory.for_date(self.briefing_date)
      print("Generated files:")
      print(f"  Briefing directory: {file_hyperlink(briefing_dir.base_path)}")
      print(f"  State: {file_hyperlink(briefing_dir.workflow_state_path)}")
      print(f"  Script: {file_hyperlink(briefing_dir.brief_json_path)}")
      if briefing_dir.consolidated_brief_json_path.exists():
        print(f"  Consolidated: {file_hyperlink(briefing_dir.consolidated_brief_json_path)}")
      if briefing_dir.master_audio_path.exists():
        print(f"  Audio: {file_hyperlink(briefing_dir.master_audio_path)}")
      print("")


class Voiceover(Command):
  print_script: bool = arg(default=False, help="do not output the audio, just print the script")
  briefing_date: date = arg(inherited=True)

  @override
  async def run(self):
    assert_env()

    from ..tts import run_voiceover

    briefing_dir = BriefingDirectory.for_date(self.briefing_date)
    briefing_dir.ensure_exists()

    briefing_script = briefing_dir.load_script()

    await run_voiceover(briefing_script, print_script=False, output_path=briefing_dir.base_path)


class LoadData(Command):
  """Loads data for the wakeup command"""

  @override
  async def run(self):
    from ..events.blogto_api import add_upcoming_blogto_events

    assert_env()

    async with get_cache():
      await add_upcoming_blogto_events()


class Server(Command):
  """Runs the wakeup server"""

  @override
  async def run(self):
    from ..server import run

    assert_env()
    await run()
