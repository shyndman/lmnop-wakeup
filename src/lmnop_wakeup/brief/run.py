import asyncio
from datetime import date, datetime, time, timedelta

import rich
from pydantic import BaseModel
from rich.markdown import Markdown

from lmnop_wakeup.tracing import langfuse_span  # Add the new import

from ..common import get_hass_api_key, get_pirate_weather_api_key
from ..locations import CoordinateLocation, LocationName, location_named
from ..tools.hass_api import get_general_information
from ..tools.weather_api import get_weather_report
from .showrunner import (
  BriefingInputs,
  calendar_events_for_briefing,
  create_showrunner,
)


class BriefingInputsSerializer(BaseModel):
  inputs: BriefingInputs


async def run(
  location: CoordinateLocation,
  todays_date: date,
):
  console = rich.console.Console()

  with langfuse_span(name="brief"):  # Replace with langfuse_span
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
    with langfuse_span(name="loading context"):  # Replace with langfuse_span
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
    console.print(Markdown(task_prompt))

    with langfuse_span(name="unleash showrunner"):  # Replace with langfuse_span
      schedule = await timekeeper_agent.run(task_prompt, deps=briefing_inputs)
      return schedule
