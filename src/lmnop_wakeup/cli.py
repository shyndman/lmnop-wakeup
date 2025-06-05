from datetime import date, timedelta
from io import StringIO
from typing import override

import clypi
import structlog
from clypi import Command, arg
from rich.prompt import Confirm

from .arg import parse_date_arg, parse_location
from .core.cache import get_cache
from .env import assert_env
from .location.model import CoordinateLocation, LocationName, location_named
from .paths import BriefingDirectory

logger = structlog.get_logger()


class Script(Command):
  """Generates a daily briefing for the users based on location and date"""

  current_location: CoordinateLocation = arg(
    location_named(LocationName.home),
    parser=parse_location,
    help="name or latlng of the user's location",
  )
  briefing_date: date = arg(inherited=True)
  review_events: bool = arg(
    default=False, short="r", help="enable interactive review of prioritized events"
  )

  @override
  async def run(self):
    from .workflow import run_workflow_command

    async with get_cache():
      assert_env()

      briefing_script = await run_workflow_command(
        briefing_date=self.briefing_date,
        briefing_location=self.current_location,
      )

      if briefing_script is None:
        return

      sb = StringIO()
      for line in briefing_script.lines:
        sb.write(f"{line.build_prompt()}\n\n")

      print(clypi.boxed(sb.getvalue(), width=80, align="left"))
      print("")

      if not Confirm.ask("Do you want to produce voiceovers?"):
        return

      await run_voiceover(self.briefing_date)


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


class Wakeup(Command):
  subcommand: Script | Voiceover | LoadData | Server

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
