from datetime import date, datetime, time, tzinfo

from pydantic import AwareDatetime, BaseModel

from pirate_weather_api_client.models import AlertsItem, Currently, Daily, Hourly, HourlyDataItem


class RegionalWeatherReports(BaseModel):
  pass


def is_timestamp_on_date(ts: int, midnight_on_date: datetime) -> bool:
  date_to_check = datetime.fromtimestamp(ts, tz=midnight_on_date.tzinfo)
  return date_to_check.date() == midnight_on_date.date()


class WeatherReport(BaseModel):
  currently: Currently
  hourly: Hourly
  daily: Daily
  alerts: list[AlertsItem]

  def trim_to_datetime(self, dt: AwareDatetime) -> "WeatherReport":
    return WeatherReport(
      currently=self.currently,
      hourly=self.hourly.trim_to_datetime(dt),
      daily=self.daily.trim_to_datetime(dt),
      alerts=self.alerts,
    )

  def get_hourlies_for_day(self, date: date, tz: tzinfo) -> list[HourlyDataItem]:
    midnight_on_date = datetime.combine(date, time(0, 0, 0), tzinfo=tz)
    hourly_data = self.hourly.data if self.hourly and self.hourly.data is not None else []

    return list(
      filter(
        lambda hour: hour.time and is_timestamp_on_date(hour.time, midnight_on_date),
        hourly_data,
      )
    )


class WeatherNotAvailable(Exception):
  pass


type WeatherResult = WeatherReport | WeatherNotAvailable
