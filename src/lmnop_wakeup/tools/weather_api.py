from datetime import date, datetime, time, tzinfo
from typing import cast

from loguru import logger
from pydantic import BaseModel

from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.errors import UnexpectedStatus
from pirate_weather_api_client.models import (
  AlertsItem,
  Currently,
  Daily,
  Hourly,
  HourlyDataItem,
  WeatherResponse200,
)

from ..common import ApiKey
from ..locations import CoordinateLocation
from ..utils.typing import nu


class WeatherNotAvailable(Exception):
  pass


def is_timestamp_on_date(ts: int, midnight_on_date: datetime) -> bool:
  date_to_check = datetime.fromtimestamp(ts, tz=midnight_on_date.tzinfo)
  return date_to_check.date() == midnight_on_date.date()


class WeatherReport(BaseModel):
  currently: Currently
  hourly: Hourly
  daily: Daily
  alerts: list[AlertsItem]

  def get_hourlies_for_day(self, date: date, tz: tzinfo) -> list[HourlyDataItem]:
    midnight_on_date = datetime.combine(date, time(0, 0, 0), tzinfo=tz)
    hourly_data = nu(self.hourly.data) if self.hourly and self.hourly.data is not None else []

    return list(
      filter(
        lambda hour: hour.time and is_timestamp_on_date(hour.time, midnight_on_date),
        hourly_data,
      )
    )


type WeatherResult = WeatherReport | WeatherNotAvailable

_API_BASE_URL = "https://api.pirateweather.net"


async def get_weather_report(
  location: CoordinateLocation,
  pirate_weather_api_key: ApiKey,
) -> WeatherReport:
  async with Client(base_url=_API_BASE_URL) as async_client:
    try:
      res = await weather.asyncio(
        api_key=pirate_weather_api_key,
        lat_and_long_or_time=f"{location.latlng[0]},{location.latlng[1]}",
        client=async_client,
        units="si",
        version=2,
        extend="hourly",
      )

      if not isinstance(res, WeatherResponse200) or res.currently is None:
        logger.error(
          "Failed to retrieve weather data or 'currently' block missing, error={error}", error=res
        )
        raise WeatherNotAvailable()

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
      raise WeatherNotAvailable()
    except Exception:
      logger.exception("An async error occurred")
      raise WeatherNotAvailable()
