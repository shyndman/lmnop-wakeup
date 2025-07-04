import asyncio
from datetime import datetime, timedelta
from typing import cast

import httpx
import structlog
from langgraph.func import task
from pydantic import AwareDatetime

from lmnop_wakeup.core.tracing import trace
from pirate_weather_api_client import Client
from pirate_weather_api_client.api.weather import weather
from pirate_weather_api_client.errors import UnexpectedStatus
from pirate_weather_api_client.models import (
  WeatherResponse200,
)

from ..core.cache import cached
from ..core.typing import assert_not_none, ensure
from ..env import ApiKey, get_pirate_weather_api_key
from ..location.model import CoordinateLocation
from .model import AlertsItem, WeatherNotAvailable, WeatherReport

logger = structlog.get_logger(__name__)
_API_BASE_URL = "https://api.pirateweather.net"


async def _get_weather_and_air_quality_data(
  location: CoordinateLocation,
  report_start_ts: AwareDatetime,
  report_end_ts: AwareDatetime | None = None,
  include_air_quality: bool = False,
  include_outdoor_comfort_hourly: bool = False,
) -> tuple[str, str | None, str | None]:
  # Caculate the span's end date
  now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
  max_end_ts = now + timedelta(days=13)
  report_end_ts = min(
    report_end_ts or now.replace(hour=23, minute=59, second=59, microsecond=999999),
    max_end_ts,
  )

  request_details = []
  weather_url = "https://api.open-meteo.com/v1/forecast"
  weather_params = {
    "latitude": location.latitude,
    "longitude": location.longitude,
    "daily": ",".join(
      [
        "sunrise",
        "sunset",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "temperature_2m_max",
        "temperature_2m_min",
        "uv_index_max",
        "uv_index_clear_sky_max",
        "snowfall_sum",
        "showers_sum",
        "rain_sum",
        "weather_code",
      ]
    ),
    "hourly": ",".join(
      [
        "temperature_2m",
        "cloud_cover_mid",
        "cloud_cover_low",
        "cloud_cover_high",
        "visibility",
        "snow_depth",
        "snowfall",
        "showers",
        "rain",
        "surface_pressure",
        "wind_direction_120m",
        "wind_speed_120m",
        "wind_gusts_10m",
        "precipitation_probability",
        "relative_humidity_2m",
      ]
    ),
    "timezone": "auto",
    "start_date": (isodate := report_start_ts.strftime("%Y-%m-%d")),
    "end_date": report_end_ts.strftime("%Y-%m-%d") if report_end_ts else isodate,
  }
  request_details.append((weather_url, weather_params))

  if include_air_quality:
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_params = {
      "latitude": location.latitude,
      "longitude": location.longitude,
      "hourly": ",".join(
        [
          "pm10",
          "pm2_5",
          "us_aqi_pm2_5",
          "us_aqi_pm10",
          "us_aqi",
          "dust",
          "carbon_monoxide",
          "carbon_dioxide",
        ]
      ),
      # TODO This will need to be revisited, for the cases where we're traveling across time zones
      "timezone": "auto",
      "start_date": (isodate := report_start_ts.strftime("%Y-%m-%d")),
      "end_date": isodate,
    }
    request_details.append((aq_url, aq_params))

  if include_outdoor_comfort_hourly:
    outdoor_comfort_url = "https://api.open-meteo.com/v1/forecast"
    outdoor_comfort_params = {
      "latitude": location.latitude,
      "longitude": location.longitude,
      "daily": "sunrise,sunset",
      "hourly": ",".join(
        [
          "apparent_temperature",
          "precipitation_probability",
          "precipitation",
          "cloud_cover",
          "cloud_cover_high",
          "cloud_cover_mid",
          "cloud_cover_low",
          "wind_speed_120m",
        ]
      ),
      "timezone": "auto",
      "start_date": (isodate := report_start_ts.strftime("%Y-%m-%d")),
      "end_date": isodate,
      # TODO(Pirate-Weather/pirateweather/issues/473): This is a suggested workaround to the issue,
      # and can be removed once it is resolved
      "exclude": "hrrr",
    }
    request_details.append((outdoor_comfort_url, outdoor_comfort_params))

  async with httpx.AsyncClient() as client:
    res = await asyncio.gather(
      *[client.get(httpx.URL(url), params=params) for url, params in request_details]
    )
    res += [None] * (3 - len(res))

    weather_res, aq_res, comfort_res = res
    if weather_res:
      weather_res.raise_for_status()
    if aq_res:
      aq_res.raise_for_status()
    if comfort_res:
      comfort_res.raise_for_status()

    return tuple(map(lambda res: res.text if res else None, res))  # type: ignore


async def _get_weather_alerts(
  location: CoordinateLocation,
  report_start_ts: AwareDatetime,
  report_end_ts: AwareDatetime | None = None,
  pirate_weather_api_key: ApiKey | None = None,
) -> list[AlertsItem]:
  async with Client(base_url=_API_BASE_URL) as async_client:
    try:
      time = f"{location.latitude},{location.longitude}"

      alert_res = await weather.asyncio(
        lat_and_long_or_time=time,
        client=async_client,
        units="ca",
        version=2,
        exclude="hrrr",
        api_key=pirate_weather_api_key or get_pirate_weather_api_key(),
      )

      if not isinstance(alert_res, WeatherResponse200) or alert_res.currently is None:
        logger.error(
          f"Failed to retrieve weather data or 'currently' block missing, error={alert_res}"
        )
        raise WeatherNotAvailable()

      alert_res = cast(WeatherResponse200, alert_res)
      logger.info(f"Async Current Temperature: {ensure(alert_res.currently).temperature}")

      alerts = assert_not_none(alert_res.alerts)
      # Filter alerts to those overlapping with the report time range
      return [
        alert
        for alert in alerts
        if alert.local_time
        and alert.local_time <= report_start_ts
        and (alert.local_expires is None or alert.local_expires >= report_start_ts)
        and (report_end_ts is None or alert.local_time <= report_end_ts)
      ]
    except UnexpectedStatus:
      logger.exception("Async API returned an unexpected status")
      raise WeatherNotAvailable()
    except Exception:
      logger.exception("An async error occurred")
      raise WeatherNotAvailable()


@trace(name="api: get_weather_report")
@cached(ttl=60 * 60 * 2)
@task()
async def get_weather_report(
  location: CoordinateLocation,
  report_start_ts: AwareDatetime,
  report_end_ts: AwareDatetime | None = None,
  include_air_quality: bool = False,
  include_comfort_hourly: bool = False,
  pirate_weather_api_key: ApiKey | None = None,
) -> WeatherReport:
  weather_data, alerts = await asyncio.gather(
    _get_weather_and_air_quality_data(
      location,
      report_start_ts=report_start_ts,
      report_end_ts=report_end_ts,
      include_air_quality=include_air_quality,
      include_outdoor_comfort_hourly=include_comfort_hourly,
    ),
    _get_weather_alerts(
      location=location,
      report_start_ts=report_start_ts,
      report_end_ts=report_end_ts,
      pirate_weather_api_key=pirate_weather_api_key,
    ),
  )
  weather_report_api_result, air_quality_api_result, comfort_api_result = weather_data
  return WeatherReport(
    location=location,
    start_ts=report_start_ts,
    end_ts=report_end_ts,
    weather_report_api_result=weather_report_api_result,
    air_quality_api_result=air_quality_api_result,
    comfort_api_result=comfort_api_result,
    alerts=alerts,
  )
