from datetime import date
from enum import Enum
from typing import override

from clypi import Command, arg
from loguru import logger

from .app import start
from .common import date_parser
from .locations import CoordinateLocation, LocationName, location_named
from .scratch.gcal import gcal_main


class Scratch(Enum):
  travel_time = 1
  gcal = 2


class LmnopWakeup(Command):
  current_location: LocationName | tuple[float, float] = arg(
    LocationName.home, help="latlon of current location"
  )
  todays_date: date = arg(
    # "%Y-%m-%d"
    date.today(),
    help="the date considered 'today' when generating the briefing",
    parser=date_parser,
  )
  scratch: Scratch | None = arg(None, hidden=True)

  @override
  async def run(self):
    logger.info("lmnop:wakeup is starting up")
    if self.scratch == Scratch.gcal:
      gcal_main()
    else:
      location = (
        location_named(self.current_location)
        if isinstance(self.current_location, LocationName)
        else CoordinateLocation(latlng=self.current_location)
      )
      await start(
        location,
        self.todays_date,
      )


def main():
  try:
    cli = LmnopWakeup.parse()
    cli.start()
  except Exception:
    logger.exception("Fatal exception")
