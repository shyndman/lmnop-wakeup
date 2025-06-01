from datetime import date, timedelta
from pathlib import Path
from typing import override

from clypi import Command, arg
from loguru import logger

from lmnop_wakeup import APP_DIRS
from lmnop_wakeup.brief.model import BriefingScript

from .arg import parse_date_arg, parse_location
from .core.cache import get_cache
from .env import assert_env
from .location.model import CoordinateLocation, LocationName, location_named


class Script(Command):
  """Generates a daily briefing for the users based on location and date"""

  current_location: CoordinateLocation = arg(
    location_named(LocationName.home),
    parser=parse_location,
    help="name or latlng of the user's location",
  )
  briefing_date: date = arg(inherited=True)
  list_checkpoints: bool = arg(
    default=False, short="l", help="list checkpoints instead of running the workflow"
  )
  review_events: bool = arg(
    default=False, short="r", help="enable interactive review of prioritized events"
  )

  @override
  async def run(self):
    from .workflow import ListCheckpoints, Run, run_workflow_command

    async with get_cache():
      assert_env()
      cmd = None
      if self.list_checkpoints:
        cmd = ListCheckpoints(briefing_date=self.briefing_date)
      else:
        cmd = Run(
          briefing_date=self.briefing_date,
          briefing_location=self.current_location,
          review_events=self.review_events,
        )
      await run_workflow_command(cmd)


class Voiceover(Command):
  script_path: Path = arg(short="i", help="path to the .json script file to voiceover")
  print_script: bool = arg(default=False, help="do not output the audio, just print the script")
  briefing_date: date = arg(inherited=True)

  @override
  async def run(self):
    from .tts import run_voiceover

    assert_env()
    script = self.script_path.open("r").read()

    path = APP_DIRS.user_state_path / self.briefing_date.isoformat()
    path.mkdir(parents=True, exist_ok=True)

    await run_voiceover(
      BriefingScript.model_validate_json(script), print_script=self.print_script, output_path=path
    )


class LoadData(Command):
  """Loads data for the wakeup command"""

  @override
  async def run(self):
    from .events.blogto_api import add_upcoming_blogto_events

    assert_env()

    async with get_cache():
      await add_upcoming_blogto_events()


class Wakeup(Command):
  subcommand: Script | Voiceover | LoadData

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
