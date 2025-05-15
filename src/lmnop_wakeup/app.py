import asyncio
from datetime import date
from encodings.punycode import generate_generalized_integer

from lmnop_wakeup.scheduler import SchedulingInputs
from lmnop_wakeup.tools.hass_api import get_general_information

from .common import get_hass_api_key, get_pirate_weather_api_key
from .locations import CoordinateLocation, LocationName, location_named
from .tools.calendar_api import get_relevant_calendar_events
from .tools.weather_api import get_weather_report

# def


async def start(
  location: CoordinateLocation,
  todays_date: date,
):
  general_info, all_cals, weather = await asyncio.gather(
    get_general_information(todays_date=todays_date, hass_api_token=get_hass_api_key()),
    get_relevant_calendar_events(todays_date, hass_api_token=get_hass_api_key()),
    get_weather_report(location, pirate_weather_api_key=get_pirate_weather_api_key()),
  )

  scheduling_inputs = SchedulingInputs(
    home_location=location_named(LocationName.home),
    todays_date=todays_date,
    is_today_work=general_info.is_today_workday,
    calendars=all_cals,
    hourly_weather=weather.get_hourlies_for_day(todays_date),
  )

  # langfuse = Langfuse()
  # prompt_res = langfuse.get_prompt("timekeeper", label="latest")
  # prompt_res.config["temperature"]
  # prompt_res.config["top_p"]
  # console = rich.console.Console(width=90)
  # console.print(Markdown(prompt_res.prompt[0]["content"]))  # type: ignore
