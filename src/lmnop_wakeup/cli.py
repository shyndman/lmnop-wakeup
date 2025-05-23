from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import override

import rich
from clypi import Command, arg
from loguru import logger

from .brief.climatologist import (
  cached_weather_report,
  create_climatologist,
)
from .common import date_parser
from .locations import CoordinateLocation, LocationName, location_named
from .schedule.run import langfuse_span, schedule

HOME = Path("~/").expanduser()


class Schedule(Command):
  """Determines tomorrow's schedule"""

  current_location: LocationName | tuple[float, float] = arg(
    LocationName.home,
    help="name or latlng of current location",
  )
  todays_date: date = arg(
    default=date.today(),
    parser=date_parser,
    help="the date considered 'today' when generating the briefing",
  )
  output: Path = arg(short="o", help="path where the schedule will be written")

  @override
  async def run(self):
    logger.info("lmnop:wakeup is starting up")
    location = (
      location_named(self.current_location)
      if isinstance(self.current_location, LocationName)
      else CoordinateLocation(latlng=self.current_location)
    )

    details = await schedule(location, self.todays_date)
    with open(self.output, "w") as f:
      f.write(details.model_dump_json())


class Brief(Command):
  """Writes and records a morning briefing based on the schedule"""

  schedule_path: Path = arg(help="Path to the output of the `schedule` command")

  @override
  async def run(self):
    pass


class Weather(Command):
  """Tests out the weather system"""

  @override
  async def run(self):
    # report = await weather_report_for_brief(location_named(LocationName.home))
    report = cached_weather_report()
    agent, *_ = await create_climatologist()
    prompt = dedent(
      f"""
      ```json
      {report.model_dump_json(indent=2)}
      ```""".strip()
    )

    console = Console(width=90)
    console.print(prompt)

    with langfuse_span("Analyzing weather data…") as span:
      res = await agent.run(prompt, deps=report)
      console.print(res)

    # async with agent.run_stream(prompt, deps=report) as res:
    #   async for message in res.stream_structured():
    #     rich.print(res)


class Wakeup(Command):
  """Root command for producing day schedules"""

  subcommand: Schedule | Brief | Weather


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except Exception:
    logger.exception("Fatal exception")
