from pydantic import AwareDatetime, BaseModel
from pydantic_extra_types.coordinate import Coordinate

from pirate_weather_api_client.models import AlertsItem

from ..location.model import CoordinateLocation


class WeatherReport(BaseModel):
  location: CoordinateLocation
  start_ts: AwareDatetime
  end_ts: AwareDatetime | None
  weather_report_api_result: str
  air_quality_api_result: str | None = None
  alerts: list[AlertsItem]

  # def trim_to_datetime(self, dt: AwareDatetime) -> "WeatherReport":
  #   return WeatherReport(
  #     location=self.location,
  #     currently=self.currently,
  #     hourly=self.hourly.trim_to_datetime(dt),
  #     daily=self.daily.trim_to_datetime(dt),
  #     alerts=[a for a in self.alerts if a.local_expires and a.local_expires > dt],
  #   )


class WeatherNotAvailable(Exception):
  pass


class RegionalWeatherReports(BaseModel):
  reports_by_latlng: dict[Coordinate, list[WeatherReport]] = {}

  def __add__(self, weather_report: WeatherReport) -> "RegionalWeatherReports":
    if weather_report.location.latlng not in self.reports_by_latlng:
      self.reports_by_latlng[weather_report.location.latlng] = []
    self.reports_by_latlng[weather_report.location.latlng].append(weather_report)
    return self


type WeatherResult = WeatherReport | WeatherNotAvailable
