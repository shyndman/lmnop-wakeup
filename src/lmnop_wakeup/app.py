import asyncio
from datetime import date

import rich
from rich.markdown import Markdown

from .common import get_hass_api_key, get_pirate_weather_api_key
from .locations import CoordinateLocation, LocationName, location_named
from .scheduler import SchedulingInputs, create_timekeeper
from .tools.hass_api import get_general_information, get_relevant_calendar_events
from .tools.weather_api import get_weather_report


async def start(
  location: CoordinateLocation,
  todays_date: date,
):
  general_info, all_cals, weather = await asyncio.gather(
    get_general_information(todays_date=todays_date, hass_api_token=get_hass_api_key()),
    get_relevant_calendar_events(todays_date, hass_api_token=get_hass_api_key()),
    get_weather_report(location, pirate_weather_api_key=get_pirate_weather_api_key()),
  )

  timekeeper_agent, instructions, prompt_templates = await create_timekeeper()
  scheduling_inputs = SchedulingInputs(
    home_location=location_named(LocationName.home),
    todays_date=todays_date,
    is_today_workday=general_info.is_today_workday,
    calendars=all_cals,
    hourly_weather=weather.get_hourlies_for_day(todays_date),
  )

  rich.print(scheduling_inputs)
  rich.print(prompt_templates)

  task_prompt = prompt_templates.format(**scheduling_inputs)

  console = rich.console.Console()
  console.print(timekeeper_agent)
  console.print(Markdown(task_prompt))

  schedule = await timekeeper_agent.run(task_prompt, deps=scheduling_inputs)
  console.print(schedule)
