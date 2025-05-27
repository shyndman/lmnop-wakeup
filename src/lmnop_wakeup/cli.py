from datetime import date, timedelta
from typing import override

from clypi import Command, arg
from loguru import logger

from .arg import parse_date_arg
from .location.model import LocationName
from .workflow import run_briefing_workflow


class Wakeup(Command):
  """Root command for producing day schedules"""

  current_location: LocationName | tuple[float, float] = arg(
    LocationName.home,
    help="name or latlng of the user's location",
  )
  briefing_date: date = arg(
    default=date.today() + timedelta(days=1),
    parser=parse_date_arg,
    help="the date of the briefing [format: YYYY-MM-DD | +N | today | tomorrow]",
  )

  @override
  async def run(self):
    await run_briefing_workflow(self.briefing_date)


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except KeyboardInterrupt:
    logger.info("lmnop:wakeup was interrupted by the user")
  except Exception:
    logger.exception("Fatal exception")
