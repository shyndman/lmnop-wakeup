from datetime import datetime
from math import floor

import structlog
from pydantic import AwareDatetime, BaseModel, Field

from pirate_weather_api_client.models import AlertsItem

from ..location.model import CoordinateLocation, ResolvedLocation

logger = structlog.get_logger(__name__)


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

  current_conditions_analysis: str | None = None
  """
    *** CONDITIONAL FIELD - ONLY POPULATE IF REPORT_DATE FALLS WITHIN WEATHER_DATA TIMEFRAME ***

    This field should ONLY be populated when the report_date provided in the input falls within
    the date range of the weather_data. If the report_date is outside the weather data timeframe,
    this field should remain None.

    When applicable, provide a detailed analysis focused specifically on the report_date. This
    analysis should complement the other sections by zooming in on that specific day and its
    immediate progression (the day itself plus next 6-12 hours).

    Focus areas:
    - Weather conditions expected for the report_date specifically
    - Hour-by-hour progression expected throughout that day
    - Actionable guidance for activities planned for the report_date
    - Any notable changes or developments expected during or shortly after that day
    - Detailed day-specific outlook that readers can reference when that date arrives
    - Specific timing for weather changes happening on the report_date

    Writing style:
    - Write as if the reader will be consulting this on the report_date itself
    - Use "today" language as if being read on that specific date
    - Be specific about timing within that day ("this morning", "this afternoon", "this evening")
    - Focus on what people can expect throughout that specific day
    - Provide actionable intelligence for planning decisions on that date
    - Write with the assumption this will be read when that date becomes "today"

    Example: "Today starts with partly cloudy skies and temperatures around 18°C this morning, but
    conditions will change significantly this afternoon. Cloud cover will increase rapidly around
    noon as that weather system approaches from the southwest. Rain will begin around 2 PM,
    starting light but becoming moderate to heavy by 4 PM - timing that could impact the evening
    commute. If you're planning outdoor activities today, wrap them up by 1:30 PM. This evening
    will remain unsettled with on-and-off showers continuing through about 9 PM before conditions
    gradually improve overnight into tomorrow."

    Remember: This field provides day-specific analysis when the report_date is within the
    forecast data. Write it as if someone will read it ON that specific day. It's NOT a summary
    of the expert_analysis - it's a detailed dive into that one particular day's progression.
    """


type WeatherKey = str


def weather_key_for_location(location: ResolvedLocation) -> WeatherKey:
  """Generates a unique key for the given location."""
  return f"{location.latitude},{location.longitude}"


class RegionalWeatherReports(BaseModel):
  reports_by_location: dict[WeatherKey, list[WeatherReport]] = {}
  analysis_by_location: dict[WeatherKey, WeatherAnalysis] = {}

  def reports_for_location(self, location: ResolvedLocation) -> list[WeatherReport]:
    """Returns the weather reports for the given location."""
    key = weather_key_for_location(location)
    return self.reports_by_location.get(key, [])

  def __add__(self, weather_report: "RegionalWeatherReports") -> "RegionalWeatherReports":
    """Merges weather_report with the receiver into a new instance"""
    new_reports = self.reports_by_location.copy()
    new_analysis = self.analysis_by_location.copy()

    for key, analysis in weather_report.reports_by_location.items():
      if key not in new_reports:
        new_reports[key] = []
      if analysis in new_reports[key]:
        logger.warning(f"Duplicate weather report for location {key} found, overwriting.")
      new_reports[key].extend(analysis)

    for key, analysis in weather_report.analysis_by_location.items():
      if key in new_analysis:
        logger.warning(f"Duplicate weather analysis for location {key} found, overwriting.")
      new_analysis[key] = analysis

    return RegionalWeatherReports(
      reports_by_location=new_reports, analysis_by_location=new_analysis
    )
