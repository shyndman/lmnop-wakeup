from typing import cast

from loguru import logger
from pydantic import BaseModel

from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.errors import UnexpectedStatus
from pirate_weather_api_client.models import AlertsItem, Currently, Hourly, WeatherResponse200
from pirate_weather_api_client.types import UNSET

from .common import ApiKey
from .typing import nu


class WeatherNotAvailable(BaseModel):
  pass


class WeatherReport(BaseModel):
  currently: Currently
  hourly: Hourly
  daily: BaseModel
  alerts: list[AlertsItem]


type WeatherResult = WeatherReport | WeatherNotAvailable


async def get_hourly_weather(
  latlon: tuple[float, float], pirate_weather_api_key: ApiKey
) -> WeatherResult:
  BASE_URL = "https://api.pirateweather.net"

  async with Client(base_url=BASE_URL) as async_client:
    try:
      res = await weather.asyncio(
        api_key=pirate_weather_api_key,
        lat_and_long_or_time=f"{latlon[0]},{latlon[1]}",
        client=async_client,
        units="si",
      )

      if not isinstance(res, WeatherResponse200) or res.currently == UNSET:
        logger.error(
          "Failed to retrieve weather data or 'currently' block missing, error={error}", error=res
        )
        return WeatherNotAvailable()

      res = cast(WeatherResponse200, res)
      logger.info("Async Current Temperature: {temp}", temp=nu(res.currently).temperature)

      return WeatherReport(
        currently=nu(res.currently),
        hourly=nu(res.hourly),
        daily=nu(res.daily),
        alerts=nu(res.alerts),
      )
    except UnexpectedStatus:
      logger.exception("Async API returned an unexpected status")
      return WeatherNotAvailable()
    except Exception:
      logger.exception("An async error occurred")
      return WeatherNotAvailable()
