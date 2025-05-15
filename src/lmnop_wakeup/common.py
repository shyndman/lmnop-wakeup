import os
from datetime import date as Date
from datetime import datetime
from datetime import datetime as DateTime
from enum import StrEnum
from typing import NewType

from pydantic import BaseModel

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


class TimeInfo(BaseModel):
  date: Date | None = None
  dateTime: DateTime | None = None

  # Validate that one and only one is provided
  def model_post_init(self, __context):
    if (self.date is None and self.dateTime is None) or (
      self.date is not None and self.dateTime is not None
    ):
      raise ValueError("Either 'date' or 'dateTime' must be provided, but not both")
