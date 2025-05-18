import asyncio
from datetime import date, datetime, time

import logfire
import rich
from pydantic import BaseModel
from rich.markdown import Markdown

from ..common import assert_not_none, get_hass_api_key, get_pirate_weather_api_key
from ..locations import CoordinateLocation, LocationName, location_named
from ..tools.hass_api import calendar_events_in_range, get_general_information
from ..tools.weather_api import get_weather_report
from .timekeeper import SchedulingDetails, SchedulingInputs, create_timekeeper


class SchedulingInputsSerializer(BaseModel):
  inputs: SchedulingInputs


async def schedule(
  location: CoordinateLocation,
  todays_date: date,
) -> SchedulingDetails:
  console = rich.console.Console()

  with logfire.span("schedule"):
    start_ts = (
      datetime.combine(todays_date, time(0))
      .astimezone()
      .replace(
        hour=0,
        minute=0,
        second=0,
      )
    )
    end_ts = start_ts.replace(hour=23, minute=59, second=59)
    hass_token = get_hass_api_key()
    general_info = all_cals = weather = None
    with logfire.span("loading context"):
      general_info, all_cals, weather = await asyncio.gather(
        get_general_information(todays_date=todays_date, hass_api_token=hass_token),
        calendar_events_in_range(start_ts=start_ts, end_ts=end_ts, hass_api_token=hass_token),
        get_weather_report(location, pirate_weather_api_key=get_pirate_weather_api_key()),
      )

    timekeeper_agent, instructions, prompt_templates = await create_timekeeper()
    scheduling_inputs = SchedulingInputs(
      home_location=location_named(LocationName.home),
      todays_date=todays_date,
      is_today_workday=general_info.is_today_workday,
      calendars=all_cals,
      hourly_weather=weather.get_hourlies_for_day(todays_date, tz=assert_not_none(start_ts.tzinfo)),
    )
    console.print(scheduling_inputs)

    serializer = SchedulingInputsSerializer(inputs=scheduling_inputs)
    model_dump = serializer.model_dump(exclude_unset=True, exclude_none=True)
    console.print(model_dump)
    task_prompt = prompt_templates.format(**model_dump["inputs"])

    with logfire.span("unleash timekeeper"):
      console.print(Markdown(task_prompt))
      schedule = await timekeeper_agent.run(task_prompt, deps=scheduling_inputs)
      return schedule.output
