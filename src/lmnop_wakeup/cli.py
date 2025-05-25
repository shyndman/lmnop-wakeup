from datetime import date, timedelta
from pathlib import Path
from textwrap import dedent
from typing import override

from clypi import Command, arg
from loguru import logger
from rich.console import Console

from .arg import parse_date_arg
from .brief import workflow
from .location.model import CoordinateLocation, LocationName, location_named
from .schedule.run import SchedulingDetails, langfuse_span, schedule
from .weather.meteorologist import (
  create_meteorologist,
  weather_report_for_brief,
)
from .workflow import run_briefing_workflow


class Schedule(Command):
  """Determines tomorrow's schedule"""

  current_location: LocationName | tuple[float, float] = arg(inherited=True)
  todays_date: date = arg(inherited=True)
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
    if not self.schedule_path.is_file():
      raise ValueError("Schedule file does not exist")

    scheduling_details = SchedulingDetails.model_validate_json(self.schedule_path.open("r").read())
    await workflow.run(scheduling_details)


class Weather(Command):
  """Tests out the weather system"""

  @override
  async def run(self):
    report = await weather_report_for_brief(location_named(LocationName.home))
    with open("weather.json", "w") as f:
      f.write(report.model_dump_json(indent=2))

    # report = cached_weather_report()

    agent, *_ = await create_meteorologist()
    prompt = dedent(
      f"""
      ```json
      {report.model_dump_json(indent=2)}
      ```""".strip()
    )

    console = Console(width=90)
    console.print(prompt)

    with langfuse_span("Analyzing weather data…"):
      res = await agent.run(prompt, deps=report)
      console.print(res)

    # async with agent.run_stream(prompt, deps=report) as res:
    #   async for message in res.stream_structured():
    #     rich.print(res)


class Wakeup(Command):
  """Root command for producing day schedules"""

  subcommand: Schedule | Brief | Weather | None

  current_location: LocationName | tuple[float, float] = arg(
    LocationName.home,
    help="name or latlng of the user's location",
  )
  todays_date: date = arg(
    default=date.today() + timedelta(days=1),
    parser=parse_date_arg,
    help="the date of the briefing [format: YYYY-MM-DD | +N | today | tomorrow]",
  )

  @override
  async def run(self):
    await run_briefing_workflow(self.todays_date)


def main():
  try:
    app = Wakeup.parse()
    app.start()
  except KeyboardInterrupt:
    logger.info("lmnop:wakeup was interrupted by the user")
  except Exception:
    logger.exception("Fatal exception")
