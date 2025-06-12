from datetime import date, timedelta
from io import StringIO
from typing import override

import clypi
import structlog
from clypi import Command, arg

from .arg import parse_date_arg, parse_location
from .core.cache import get_cache
from .core.terminal import is_interactive_terminal
from .env import assert_env
from .location.model import CoordinateLocation, LocationName, location_named
from .paths import BriefingDirectory

logger = structlog.get_logger()


def should_prompt_user() -> bool:
  """Check if we should prompt the user for interactive input.

  Returns True if we're in an interactive terminal, False otherwise.
  This is used as the default for human-in-the-loop workflow steps.
  """
  return is_interactive_terminal()


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
    from .workflow import WorkflowAbortedByUser, run_workflow

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

      sb = StringIO()
      for line in briefing_script.lines:
        sb.write(f"{line.build_prompt()}\n\n")

      print(clypi.boxed(sb.getvalue(), width=80, align="left"))
      print("")


class Voiceover(Command):
  print_script: bool = arg(default=False, help="do not output the audio, just print the script")
  briefing_date: date = arg(inherited=True)

  @override
  async def run(self):
    assert_env()

    await run_voiceover(self.briefing_date)


async def run_voiceover(date):
  from .tts import run_voiceover

  briefing_dir = BriefingDirectory.for_date(date)
  briefing_dir.ensure_exists()

  briefing_script = briefing_dir.load_script()

  await run_voiceover(briefing_script, print_script=False, output_path=briefing_dir.base_path)


class LoadData(Command):
  """Loads data for the wakeup command"""

  @override
  async def run(self):
    from .events.blogto_api import add_upcoming_blogto_events

    assert_env()

    async with get_cache():
      await add_upcoming_blogto_events()


class Server(Command):
  """Runs the wakeup server"""

  @override
  async def run(self):
    from .server import run

    assert_env()
    await run()


class ThemeMusic(Command):
  """Add theme music to an existing briefing"""

  briefing_date: date = arg(inherited=True)

  @override
  async def run(self):
    from .audio.theme import ThemeMusicConfig, ThemeMusicMixer
    from .paths import get_theme_intro_path, get_theme_music_path

    assert_env()

    briefing_dir = BriefingDirectory.for_date(self.briefing_date)

    if not briefing_dir.exists():
      print(f"No briefing directory found for {self.briefing_date}")
      return

    if not briefing_dir.briefing_audio_path.exists():
      print(f"No briefing audio found at {briefing_dir.briefing_audio_path}")
      return

    # Load the consolidated script for timing
    try:
      consolidated_script_path = briefing_dir.consolidated_brief_json_path
      if consolidated_script_path.exists():
        from .brief.model import ConsolidatedBriefingScript

        script_content = consolidated_script_path.read_text()
        script = ConsolidatedBriefingScript.model_validate_json(script_content)
      else:
        # Fallback to regular script and consolidate it
        script = briefing_dir.load_script()
        script = script.consolidate_dialogue()
    except Exception as e:
      print(f"Error loading briefing script: {e}")
      return

    # Get theme music paths
    theme_music_path = get_theme_music_path()
    theme_intro_path = get_theme_intro_path()

    if not theme_music_path.exists():
      print(f"Theme music file not found at {theme_music_path}")
      print("You can set a custom theme music path with THEME_MUSIC_PATH environment variable")
      return

    if not theme_intro_path.exists():
      print(f"Theme intro file not found at {theme_intro_path}")
      print("You can set a custom theme intro path with THEME_INTRO_PATH environment variable")
      return

    # Mix theme music with briefing
    mixer = ThemeMusicMixer(ThemeMusicConfig())

    try:
      output_path = mixer.mix_theme_with_briefing(
        briefing_audio_path=briefing_dir.briefing_audio_path,
        theme_music_path=theme_music_path,
        theme_intro_path=theme_intro_path,
        script=script,
        audio_files_dir=briefing_dir.base_path,
        output_path=briefing_dir.master_audio_path,
      )
      print(f"Theme music added successfully: {output_path}")
    except Exception as e:
      print(f"Error adding theme music: {e}")


class Wakeup(Command):
  subcommand: Script | Voiceover | LoadData | Server | ThemeMusic

  briefing_date: date = arg(
    default=date.today() + timedelta(days=1),
    parser=parse_date_arg,
    help="the date of the briefing [format: YYYY-MM-DD | +N | today | tomorrow]",
  )


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except KeyboardInterrupt:
    logger.info("lmnop:wakeup was interrupted by the user")
  except Exception:
    logger.exception("Fatal exception")
