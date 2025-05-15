from datetime import date
from typing import override

from clypi import Command, arg
from loguru import logger

from .app import start
from .common import date_parser
from .locations import CoordinateLocation, LocationName, location_named


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

  @override
  async def run(self):
    logger.info("lmnop:wakeup is starting up")
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
