from typing import cast

import httpx
from loguru import logger
from pydantic import AwareDatetime, BaseModel

from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.errors import UnexpectedStatus
from pirate_weather_api_client.models import (
  WeatherResponse200,
)

from ..core.typing import assert_not_none, ensure
from ..env import ApiKey, get_pirate_weather_api_key
from ..location.model import CoordinateLocation
from .model import WeatherNotAvailable, WeatherReport

_API_BASE_URL = "https://api.pirateweather.net"

# https://api.open-meteo.com/v1/forecast?latitude=43.69107214185943&longitude=-79.3077542870965&daily=sunset&hourly=cloud_cover_low,cloud_cover_mid,cloud_cover_high,visibility,cloud_cover,precipitation,pressure_msl&timezone=America%2FNew_York&start_date=2025-05-27&end_date=2025-05-27


class SunsetWeatherData(BaseModel):
  json_blob: str


async def get_sunset_weather_data(location: CoordinateLocation, prediction_date: AwareDatetime):
  # Make sure all required weather variables are listed here
  # The order of variables in hourly or daily is important to assign them correctly below
  url = "https://api.open-meteo.com/v1/forecast"
  params = {
    "latitude": location.latitude,
    "longitude": location.longitude,
    "daily": "sunset",
    "hourly": ",".join(
      [
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
        "visibility",
        "cloud_cover",
        "precipitation",
        "pressure_msl",
        "surface_pressure",
      ]
    ),
    "timezone": assert_not_none(prediction_date.tzinfo).tzname,
    "start_date": (isodate := prediction_date.strftime("%Y-%m-%d")),
    "end_date": isodate,
  }
  async with httpx.AsyncClient() as client:
    response = await client.get(httpx.URL(url), params=params)
    response.raise_for_status()
    return SunsetWeatherData(json_blob=response.text)


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
      logger.info("Async Current Temperature: {temp}", temp=ensure(res.currently).temperature)

      return WeatherReport(
        currently=ensure(res.currently),
        hourly=ensure(res.hourly),
        daily=ensure(res.daily),
        alerts=ensure(res.alerts),
      )
    except UnexpectedStatus:
      logger.exception("Async API returned an unexpected status")
      raise WeatherNotAvailable()
    except Exception:
      logger.exception("An async error occurred")
      raise WeatherNotAvailable()
