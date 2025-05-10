import asyncio
import os
import sys
from datetime import date
from enum import StrEnum

import click
import rich
from loguru import logger

from llmop_wakeup.weather import get_hourly_weather

from .calendars import get_todays_calendar_events
from .common import ApiKey

logger.remove()
logger.add(
  sys.stderr,
  format="<green>{time:HH:mm:ss}</green> "
  "<dim>[%d]</dim> <level>{level} {message}</level>" % os.getpid(),
)


class EnvName(StrEnum):
  GEMINI_API_KEY = "GEMINI_API_KEY"
  HASS_API_TOKEN = "HASS_API_TOKEN"
  PIRATE_WEATHER_API_KEY = "PIRATE_WEATHER_API_KEY"


async def start(
  latlon: tuple[float, float],
  today_override: date | None,
  hass_api_token: ApiKey,
  gemini_api_key: ApiKey,
  pirate_weather_api_key: ApiKey,
):
  weather, all_cals = await asyncio.gather(
    get_hourly_weather(latlon, pirate_weather_api_key),
    get_todays_calendar_events(today_override, hass_api_token),
  )
  rich.print(weather)
  rich.print(all_cals)


@click.command()
@click.option(
  "--latlon",
  nargs=2,
  type=(float, float),
  default="43.69086460515023 -79.30780076686716",
  help="Location for weather report",
)
@click.option(
  "--today-override",
  type=date,
  default=None,
  help="Overrides today's date for testing",
)
def main(latlon: tuple[float, float], today_override: date | None):
  logger.info("llmop:wakeup is starting up")

  if EnvName.HASS_API_TOKEN not in os.environ:
    raise EnvironmentError(f"Missing {EnvName.HASS_API_TOKEN}")
  if EnvName.GEMINI_API_KEY not in os.environ:
    raise EnvironmentError(f"Missing {EnvName.GEMINI_API_KEY}")
  if EnvName.PIRATE_WEATHER_API_KEY not in os.environ:
    raise EnvironmentError(f"Missing {EnvName.PIRATE_WEATHER_API_KEY}")

  hass_api_token = ApiKey(os.environ.get(EnvName.HASS_API_TOKEN) or "")  # or is for type checker
  gemini_api_key = ApiKey(os.environ.get(EnvName.GEMINI_API_KEY) or "")
  pirate_weather_api_key = ApiKey(os.environ.get(EnvName.PIRATE_WEATHER_API_KEY) or "")

  asyncio.run(start(latlon, today_override, hass_api_token, gemini_api_key, pirate_weather_api_key))
