import asyncio
from datetime import date, datetime, time, timedelta

import logfire
import rich
from pydantic import BaseModel
from rich.markdown import Markdown

from lmnop_wakeup.brief.showrunner import (
  BriefingInputs,
  calendar_events_for_briefing,
  create_showrunner,
)
from lmnop_wakeup.cli import CoordinateLocation
from lmnop_wakeup.common import get_hass_api_key, get_pirate_weather_api_key
from lmnop_wakeup.locations import LocationName, location_named
from lmnop_wakeup.tools.hass_api import get_general_information
from lmnop_wakeup.tools.weather_api import get_weather_report


class BriefingInputsSerializer(BaseModel):
  inputs: BriefingInputs


async def run(
  location: CoordinateLocation,
  todays_date: date,
):
  console = rich.console.Console()

  with logfire.span("brief"):
    start_ts = (
      datetime.combine(todays_date, time(0))
      .astimezone()
      .replace(
        hour=0,
        minute=0,
        second=0,
      )
    )
    end_ts = start_ts.replace(hour=23, minute=59, second=59) + timedelta(days=30)
    hass_token = get_hass_api_key()
    general_info = all_cals = weather = None
    with logfire.span("loading context"):
      general_info, all_cals, weather = await asyncio.gather(
        get_general_information(todays_date=todays_date, hass_api_token=hass_token),
        calendar_events_for_briefing(start_ts=start_ts, end_ts=end_ts),
        get_weather_report(location, pirate_weather_api_key=get_pirate_weather_api_key()),
      )

    timekeeper_agent, instructions, prompt_templates = await create_showrunner()
    briefing_inputs = BriefingInputs(
      home_location=location_named(LocationName.home),
      todays_date=todays_date,
      current_weather=weather.currently,
      hourly_weather=weather.hourly,
      daily_weather=weather.daily,
      is_today_workday=general_info.is_today_workday,
      calendars=all_cals,
    )
    console.print(briefing_inputs)

    serializer = BriefingInputsSerializer(inputs=briefing_inputs)
    model_dump = serializer.model_dump(exclude_unset=True, exclude_none=True)
    console.print(model_dump)
    task_prompt = prompt_templates.format(**model_dump["inputs"])

    with logfire.span("unleash showrunner"):
      console.print(Markdown(task_prompt))
      schedule = await timekeeper_agent.run(task_prompt, deps=briefing_inputs)
      return schedule
