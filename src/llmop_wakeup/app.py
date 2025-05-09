import asyncio
import os
import sys
from enum import StrEnum

import rich
from loguru import logger

from llmop_wakeup.entity import EntityId, get_entity_state

from .calendars import get_todays_calendar_events
from .common import ApiKey

logger.remove()
logger.add(
  sys.stderr,
  format="<green>{time:HH:mm:ss}</green> <dim>[%d]</dim> <level>{level} {message}</level>"
  % os.getpid(),
)


class Env(StrEnum):
  GEMINI_API_KEY = "GEMINI_API_KEY"
  HASS_API_TOKEN = "HASS_API_TOKEN"


async def start(hass_api_token: ApiKey, gemini_api_key: ApiKey):
  pirate_weather = await get_entity_state(hass_api_token, EntityId("weather.pirate_toronto"))
  rich.print(pirate_weather)

  all_cals = await get_todays_calendar_events(hass_api_token)
  rich.print(all_cals)


def main():
  logger.info("llmop:wakeup is starting up")

  if Env.HASS_API_TOKEN not in os.environ:
    raise EnvironmentError(f"Missing {Env.HASS_API_TOKEN}")
  if Env.GEMINI_API_KEY not in os.environ:
    raise EnvironmentError(f"Missing {Env.GEMINI_API_KEY}")

  hass_api_token = ApiKey(os.environ.get(Env.HASS_API_TOKEN) or "")  # or is for type checker
  gemini_api_key = ApiKey(os.environ.get(Env.GEMINI_API_KEY) or "")

  asyncio.run(start(hass_api_token, gemini_api_key))
