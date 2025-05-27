from typing import cast

from loguru import logger
from pydantic import AwareDatetime

from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.errors import UnexpectedStatus
from pirate_weather_api_client.models import (
  WeatherResponse200,
)

from ..core.typing import nn
from ..env import ApiKey, get_pirate_weather_api_key
from ..location.model import CoordinateLocation
from .model import WeatherNotAvailable, WeatherReport

_API_BASE_URL = "https://api.pirateweather.net"


async def get_weather_report(
  location: CoordinateLocation,
  report_start_ts: AwareDatetime,
  report_end_ts: AwareDatetime | None = None,
  pirate_weather_api_key: ApiKey | None = None,
) -> WeatherReport:
  async with Client(base_url=_API_BASE_URL) as async_client:
    try:
      posix_time = int(report_start_ts.timestamp())
      spacetime = f"{location.latitude},{location.longitude},{posix_time}"

      res = await weather.asyncio(
        lat_and_long_or_time=spacetime,
        client=async_client,
        units="ca",
        version=2,
        extend="hourly",
        exclude="minutely",
        api_key=pirate_weather_api_key or get_pirate_weather_api_key(),
      )

      if not isinstance(res, WeatherResponse200) or res.currently is None:
        logger.error(
          "Failed to retrieve weather data or 'currently' block missing, error={error}", error=res
        )
        raise WeatherNotAvailable()

      res = cast(WeatherResponse200, res)
      logger.info("Async Current Temperature: {temp}", temp=nn(res.currently).temperature)

      return WeatherReport(
        currently=nn(res.currently),
        hourly=nn(res.hourly),
        daily=nn(res.daily),
        alerts=nn(res.alerts),
      )
    except UnexpectedStatus:
      logger.exception("Async API returned an unexpected status")
      raise WeatherNotAvailable()
    except Exception:
      logger.exception("An async error occurred")
      raise WeatherNotAvailable()
