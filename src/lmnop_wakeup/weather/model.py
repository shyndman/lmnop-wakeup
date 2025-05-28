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

  def __add__(self, weather_report: "RegionalWeatherReports") -> "RegionalWeatherReports":
    """Merges weather_report with the receiver into a new instance"""
    new_reports = self.reports_by_latlng.copy()
    for latlng, reports in weather_report.reports_by_latlng.items():
      if latlng not in new_reports:
        new_reports[latlng] = []
      new_reports[latlng].extend(reports)
    return RegionalWeatherReports(reports_by_latlng=new_reports)


type WeatherResult = WeatherReport | WeatherNotAvailable
