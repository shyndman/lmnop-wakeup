from datetime import date, timedelta
from typing import override

from clypi import Command, arg
from loguru import logger

from .arg import parse_date_arg, parse_location
from .core.cache import get_cache
from .env import assert_env
from .location.model import CoordinateLocation, LocationName, location_named
from .workflow import ListCheckpoints, Run, run_workflow_command


class Wakeup(Command):
  """Generates a daily briefing for the users based on location and date"""

  current_location: CoordinateLocation = arg(
    location_named(LocationName.home),
    parser=parse_location,
    help="name or latlng of the user's location",
  )
  briefing_date: date = arg(
    default=date.today() + timedelta(days=1),
    parser=parse_date_arg,
    help="the date of the briefing [format: YYYY-MM-DD | +N | today | tomorrow]",
  )
  list_checkpoints: bool = arg(
    default=False, short="l", help="list checkpoints instead of running the workflow"
  )

  @override
  async def run(self):
    async with get_cache():
      assert_env()
      cmd = None
      if self.list_checkpoints:
        cmd = ListCheckpoints(briefing_date=self.briefing_date)
      else:
        cmd = Run(briefing_date=self.briefing_date, briefing_location=self.current_location)
      await run_workflow_command(cmd)


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except KeyboardInterrupt:
    logger.info("lmnop:wakeup was interrupted by the user")
  except Exception:
    logger.exception("Fatal exception")
