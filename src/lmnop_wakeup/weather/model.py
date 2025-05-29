from pydantic import AwareDatetime, BaseModel
from pydantic_extra_types.coordinate import Coordinate

from pirate_weather_api_client.models import AlertsItem

from ..location.model import CoordinateLocation, ResolvedLocation
from .meteorologist_agent import WeatherAnalysis


class WeatherReport(BaseModel):
  location: CoordinateLocation
  start_ts: AwareDatetime
  end_ts: AwareDatetime | None
  weather_report_api_result: str
  air_quality_api_result: str | None = None
  alerts: list[AlertsItem]


class WeatherNotAvailable(Exception):
  pass


type RegionalWeatherKey = tuple[str, Coordinate]


class RegionalWeatherReports(BaseModel):
  reports_by_location: dict[ResolvedLocation, list[WeatherReport]] = {}
  analysis_by_location: dict[ResolvedLocation, WeatherAnalysis] = {}

  def reports_for_location(self, location: ResolvedLocation) -> list[WeatherReport]:
    """Returns the weather reports for the given location."""
    return self.reports_by_location.get(location, [])

  def __add__(self, weather_report: "RegionalWeatherReports") -> "RegionalWeatherReports":
    """Merges weather_report with the receiver into a new instance"""
    new_reports = self.reports_by_location.copy()
    for latlng, reports in weather_report.reports_by_location.items():
      if latlng not in new_reports:
        new_reports[latlng] = []
      new_reports[latlng].extend(reports)
    return RegionalWeatherReports(reports_by_location=new_reports)


type WeatherResult = WeatherReport | WeatherNotAvailable
