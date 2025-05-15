import os
from datetime import date as Date
from datetime import datetime
from enum import StrEnum
from typing import NewType

from lmnop_wakeup.typing import assert_not_none

ApiKey = NewType("ApiKey", str)


def api_key_parser(raw: str | list[str]) -> ApiKey:
  if isinstance(raw, list):
    raise ValueError("List input not supported")
  if len(raw.strip()) == 0:
    raise ValueError("API key may not be empty")
  return ApiKey(raw)


def date_parser(raw: str | list[str]) -> Date:
  if isinstance(raw, list):
    raise ValueError("List input not supported")
  return datetime.strptime(raw, "%Y-%m-%d").date()


class EnvName(StrEnum):
  GEMINI_API_KEY = "GEMINI_API_KEY"
  HASS_API_TOKEN = "HASS_API_TOKEN"
  PIRATE_WEATHER_API_KEY = "PIRATE_WEATHER_API_KEY"
  GOOGLE_ROUTES_API_KEY = "GOOGLE_ROUTES_API_KEY"
  LANGFUSE_PUBLIC_KEY = "LANGFUSE_PUBLIC_KEY"
  LANGFUSE_SECRET_KEY = "LANGFUSE_SECRET_KEY"
  LANGFUSE_HOST = "LANGFUSE_HOST"


def get_hass_api_key() -> ApiKey:
  return ApiKey(assert_not_none(os.getenv(EnvName.HASS_API_TOKEN)))


def get_pirate_weather_api_key() -> ApiKey:
  return ApiKey(assert_not_none(os.getenv(EnvName.PIRATE_WEATHER_API_KEY)))


def get_google_routes_api_key() -> ApiKey:
  return ApiKey(assert_not_none(os.getenv(EnvName.GOOGLE_ROUTES_API_KEY)))


def assert_env():
  for name in list(EnvName):
    if name not in os.environ:
      raise EnvironmentError(f"Required environment variable {name} not provided")
