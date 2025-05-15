import asyncio
from datetime import date, datetime

import rich

from .common import get_google_routes_api_key, get_hass_api_key, get_pirate_weather_api_key
from .locations import NAMED_LOCATIONS, CoordinateLocation, LocationName
from .tools.calendars import get_relevant_calendar_events
from .tools.routes_api import ArriveByConstraint, compute_route_durations
from .tools.weather import get_hourly_weather


async def start(
  location: CoordinateLocation,
  todays_date: date,
):
  now = datetime.now().astimezone()
  arrival_time = now.replace(hour=12, minute=0, second=5)

  routes, weather, all_cals = await asyncio.gather(
    compute_route_durations(
      get_google_routes_api_key(),
      origin=NAMED_LOCATIONS[LocationName.home],
      destination=NAMED_LOCATIONS[LocationName.hilarys_moms_house],
      time_constraint=ArriveByConstraint(time=arrival_time),
      include_cycling=True,
      include_transit=True,
      include_walking=True,
    ),
    get_hourly_weather(location.latlng, get_pirate_weather_api_key()),
    get_relevant_calendar_events(todays_date, get_hass_api_key()),
  )

  console = rich.get_console()
  # console.print(all_cals)
  # console.print(weather)
  console.print(routes)

  # langfuse = Langfuse()
  # prompt_res = langfuse.get_prompt("timekeeper", label="latest")
  # prompt_res.config["temperature"]
  # prompt_res.config["top_p"]
  # console = rich.console.Console(width=90)
  # console.print(Markdown(prompt_res.prompt[0]["content"]))  # type: ignore
