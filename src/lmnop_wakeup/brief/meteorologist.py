import json
from datetime import datetime
from importlib import resources

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from pirate_weather_api_client.models import AlertsItem, Currently, Daily, Hourly

from ..common import get_pirate_weather_api_key
from ..llm import GEMINI_25_FLASH, create_litellm_model, get_langfuse_prompt_bundle
from ..locations import NamedLocation
from .run import get_weather_report


class RawWeatherData(BaseModel):
  alerts: list[AlertsItem]
  currently: Currently
  hourly: Hourly
  daily: Daily


class WeatherPattern(BaseModel):
  """A group of days with similar weather conditions"""

  pattern_type: str = Field(
    ...,
    description="The type of weather pattern (e.g., 'Sunny and Warm', 'Rainy', 'Cool and Cloudy')",
  )
  """
    The descriptive name of this weather pattern. Be specific but concise.

    Examples:
    - "Warm and Breezy"
    - "Cold Front Passage"
    - "Summer Thunderstorm Pattern"
    - "Clear but Chilly"
    - "Humid with Afternoon Showers"
    """

  days: list[datetime] = Field(
    ...,
    description="The dates that share this weather pattern",
  )
  """
    The specific dates that share this weather pattern. Use the date format from the JSON data.
    Include all dates that fit this pattern, even if they're not consecutive.

    Example: ['2025-05-19', '2025-05-20', '2025-05-23'] would indicate three non-consecutive
    days sharing similar conditions.
    """

  characteristics: str = Field(
    ...,
    max_length=1200,
    description="Key characteristics of this weather pattern as descriptive text (temp range, "
    "precip chance, etc.)",
  )
  """
    Detailed description of this weather pattern's key characteristics as flowing text.

    Include: - Temperature ranges (highs and lows) - Precipitation chances and types - Wind
    conditions (speed, direction, gusts) - Cloud cover patterns - Humidity levels - UV index and sun
    exposure - Any notable features (fog, frost, etc.)

    Example: "This pattern features daytime highs of 15-17°C with overnight lows around 8-10°C.
    Winds remain light (5-10 km/h) from the northwest with moderate humidity (50-65%). Cloud cover
    increases in the afternoons to about 70% coverage, but precipitation chances remain low (<20%).
    Daily UV index peaks around 6-7, indicating moderate sun exposure risk."
    """


class WeatherReportForBrief(BaseModel):
  """Weather analysis with pattern groupings and weatherperson script"""

  expert_analysis: str = Field(
    ...,
    max_length=1200,
    description="Expert meteorologist analysis of patterns and trends as descriptive text",
  )
  """
    Expert meteorological analysis written as flowing text. Analyze the forecast holistically,
    discussing notable meteorological features, confidence levels, and interesting patterns.

    Include: - Dominant weather systems affecting the period - Notable transitions or frontal
    passages - Confidence assessment of different aspects of the forecast - Unusual or noteworthy
    features for the time of year - Potential hazards or concerns - Broader context of the weather
    pattern

    Example: "This forecast period shows a classic late spring transition pattern for the Great
    Lakes region. The initial ridge of high pressure will gradually break down as a trough
    approaches from the northwest, bringing increasing moisture and instability by midweek. Diurnal
    temperature variations remain significant (8-10°C daily swing), typical for clear conditions
    this time of year. Confidence is high for the temperature forecast through day 3, but
    precipitation timing becomes increasingly uncertain beyond that point, particularly regarding
    the speed of the approaching frontal boundary."
    """

  weather_patterns: list[WeatherPattern] = Field(
    ...,
    description="Groups of days with similar weather conditions, ordered chronologically",
  )
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

  weatherperson_script: str = Field(
    ...,
    description="Conversational weather report written in a casual, engaging style",
  )
  """
    A friendly, conversational weather report similar to what a TV meteorologist might deliver.

    Guidelines: - Use a casual, engaging tone that connects with viewers - Avoid technical jargon
    unless explaining it in simple terms - Group similar days together for narrative flow - Mention
    specific locations where relevant (parks, lakes, etc.) - Include practical advice for planning -
    Add personality and conversational elements - Use accessible analogies to explain weather
    concepts

    Example style: "Good morning, Toronto! We've got a real mix of weather coming our way this week.
    Today and tomorrow will be absolutely gorgeous with plenty of sunshine and temperatures climbing
    to a comfortable 22 degrees. Perfect weather for hitting the waterfront trail or enjoying dinner
    on a patio! But don't get too comfortable - by Wednesday, we're watching a system moving in from
    the west that's going to bring some potentially heavy downpours, especially during the afternoon
    commute. If you've got outdoor plans for Wednesday, your best bet is the morning hours before
    those rain chances ramp up..."

    Write a complete script that covers the entire forecast period in a flowing, natural way. You
    should aim for about a minute of speaking time, or 150-200 words.
    """

  # key_recommendations: list[str] | None = Field(
  #   [],
  #   description="Optional list of key takeaways or recommendations for planning",
  # )
  """
    A concise list of the most important planning recommendations based on the forecast.

    These should be practical, actionable takeaways that help with decision-making.

    Examples:
    - "Plan outdoor activities for Monday and Tuesday; avoid Wednesday afternoon"
    - "Best cottage/beach weather comes this weekend - Friday through Sunday"
    - "Pack both warm and cool weather clothing as temperatures will vary significantly"
    - "Morning hours consistently offer the best conditions for outdoor exercise"
    - "Wednesday afternoon carries significant rain risk - have indoor alternatives ready"

    Include 3-7 key recommendations that capture the most important planning insights.
    """


type MeteorologistAgent = Agent[RawWeatherData, WeatherReportForBrief]


async def create_meteorologist(model: str = GEMINI_25_FLASH) -> tuple[MeteorologistAgent, str, str]:
  bundle = await get_langfuse_prompt_bundle("meteorologist")

  meteorologist = Agent(
    model=create_litellm_model(model),
    instructions=bundle.instructions,
    deps_type=RawWeatherData,
    output_type=WeatherReportForBrief,
    model_settings=bundle.model_settings,
    # mcp_servers=[sandboxed_python_mcp_server()],
    instrument=True,
  )

  @meteorologist.tool_plain()
  def posix_to_local_time(posix: int) -> datetime:
    return datetime.fromtimestamp(posix).astimezone()

  return meteorologist, bundle.instructions, bundle.task_prompt_templates


async def weather_report_for_brief(location: NamedLocation):
  r = await get_weather_report(location, pirate_weather_api_key=get_pirate_weather_api_key())
  return RawWeatherData(alerts=r.alerts, currently=r.currently, hourly=r.hourly, daily=r.daily)


def cached_weather_report() -> RawWeatherData:
  """
  Load the weather.json file as a resource.

  Returns:
      dict: The parsed JSON data from the weather.json file.
  """
  with resources.files("lmnop_wakeup.brief").joinpath("weather.json").open("r") as f:
    return RawWeatherData.model_validate(json.load(f))
