from datetime import datetime
from math import floor

from loguru import logger
from pydantic import AwareDatetime, BaseModel, Field

from pirate_weather_api_client.models import AlertsItem

from ..location.model import CoordinateLocation, ResolvedLocation


class WeatherReport(BaseModel):
  location: CoordinateLocation
  start_ts: AwareDatetime
  end_ts: AwareDatetime | None
  weather_report_api_result: str
  air_quality_api_result: str | None = None
  comfort_api_result: str | None = None
  alerts: list[AlertsItem]


class WeatherNotAvailable(Exception):
  pass


class WeatherPattern(BaseModel):
  """A group of days with similar weather conditions"""

  pattern_type: str = Field()
  """
    The descriptive name of this weather pattern. Be specific but concise.

    Examples:
    - "Warm and Breezy"
    - "Cold Front Passage"
    - "Summer Thunderstorm Pattern"
    - "Clear but Chilly"
    - "Humid with Afternoon Showers"
    """

  days: list[datetime] = Field()
  """
    The specific dates that share this weather pattern. Use the date format from the JSON data.
    Include all dates that fit this pattern, even if they're not consecutive.

    Example: ['2025-05-19T00:00:00', '2025-05-20T00:00:00', '2025-05-23T00:00:00'] would indicate
    three non-consecutive days sharing similar conditions.
    """

  characteristics: str = Field(max_length=floor(5 * 100))
  """
    Semi-details description of this weather pattern's key characteristics as flowing text. Maximum
    of around 100 words, but aim for ~70.

    Include: - Temperature ranges (highs and lows) - Precipitation chances and types - Wind
    conditions (speed, direction, gusts) - Cloud cover patterns - Humidity levels - UV index and sun
    exposure - Any notable features (fog, frost, etc.)

    Example: "This pattern features daytime highs of 15-17°C with overnight lows around 8-10°C.
    Winds remain light (5-10 km/h) from the northwest with moderate humidity (50-65%). Cloud cover
    increases in the afternoons to about 70% coverage, but precipitation chances remain low (<20%).
    Daily UV index peaks around 6-7, indicating moderate sun exposure risk."

    IMPORTANT! If the input data contains alerts, YOU MUST mention them in the characteristics
    for their dates. It is a matter of safety.
    """


class WeatherAnalysis(BaseModel):
  """Weather analysis with pattern groupings and weatherperson script"""

  expert_analysis: str
  """
    Expert meteorological analysis written as flowing text. Analyze the forecast holistically,
    discussing notable meteorological features, confidence levels, and interesting patterns.

    Include: - Dominant weather systems affecting the period - Notable transitions or frontal
    passages - Confidence assessment of different aspects of the forecast - Unusual or noteworthy
    features for the time of year - Potential hazards or concerns - Broader context of the weather
    pattern - Information communicate through "alerts" in the input.

    Example: "This forecast period shows a classic late spring transition pattern for the Great
    Lakes region. The initial ridge of high pressure will gradually break down as a trough
    approaches from the northwest, bringing increasing moisture and instability by midweek. Diurnal
    temperature variations remain significant (8-10°C daily swing), typical for clear conditions
    this time of year. Confidence is high for the temperature forecast through day 3, but
    precipitation timing becomes increasingly uncertain beyond that point, particularly regarding
    the speed of the approaching frontal boundary."

    If your input data contains alerts, YOU MUST mention them in the weather patterns. It is a
    matter of safety.
    """

  weather_patterns: list[WeatherPattern] = Field()
  """
    Grouped days with similar weather patterns, organized so other systems can easily reference
    them.

    Each pattern should group days with genuinely similar conditions. There's no fixed number of
    patterns - use your expertise to determine how many distinct patterns exist in the forecast
    period.

    Patterns should be ordered chronologically based on when they first appear in the forecast.

    A day should only belong to one pattern. If a day is transitional, assign it to the pattern that
    best characterizes the majority of that day.
    """

  weatherperson_script: str
  """
    A friendly, conversational weather report similar to what a TV meteorologist might deliver.

    Guidelines: - Use a casual, engaging tone that connects with viewers - Avoid technical jargon
    unless explaining it in simple terms - Group similar days together for narrative flow - Mention
    specific nearby locations where relevant (parks, lakes, etc.). Add personality and
    conversational elements - Use accessible analogies to explain weather concepts

    Example style: "Good morning, Toronto! We've got a real mix of weather coming our way this week.
    Today and tomorrow will be absolutely gorgeous with plenty of sunshine and temperatures climbing
    to a comfortable 22 degrees, but don't get too comfortable - by Wednesday, we're watching a
    system moving in from the west that's going to bring some potentially heavy downpours,
    especially during the afternoon commute. If you've got outdoor plans for Wednesday, your best
    bet is the morning hours before those rain chances ramp up."

    Write a complete script that covers the entire forecast period in a flowing, natural way. You
    should aim for about a minute of speaking time, or 100-200 words.
    """


class RegionalWeatherReports(BaseModel):
  reports_by_location: dict[ResolvedLocation, list[WeatherReport]] = {}
  analysis_by_location: dict[ResolvedLocation, WeatherAnalysis] = {}

  def reports_for_location(self, location: ResolvedLocation) -> list[WeatherReport]:
    """Returns the weather reports for the given location."""
    return self.reports_by_location.get(location, [])

  def __add__(self, weather_report: "RegionalWeatherReports") -> "RegionalWeatherReports":
    """Merges weather_report with the receiver into a new instance"""
    new_reports = self.reports_by_location.copy()
    new_analysis = self.analysis_by_location.copy()

    for loc, analysis in weather_report.reports_by_location.items():
      if loc not in new_reports:
        new_reports[loc] = []
      if analysis in new_reports[loc]:
        logger.warning(f"Duplicate weather report for location {loc} found, skipping addition.")
        continue
      new_reports[loc].extend(analysis)

    for loc, analysis in weather_report.analysis_by_location.items():
      if loc in new_analysis:
        raise ValueError(f"Location {loc} already has reports, cannot overwrite with analysis.")
      new_analysis[loc] = analysis

    return RegionalWeatherReports(
      reports_by_location=new_reports, analysis_by_location=new_analysis
    )
