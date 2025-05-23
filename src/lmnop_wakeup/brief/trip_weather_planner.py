import json
from datetime import date, datetime
from importlib import resources

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ..common import get_pirate_weather_api_key
from ..llm import GEMINI_25_FLASH, create_litellm_model, get_langfuse_prompt_bundle
from ..locations import NamedLocation
from .run import CoordinateLocation, get_weather_report


class LocationWeatherRequest(BaseModel):
  """A request for more information about the weather at a location over a range of dates"""

  location: NamedLocation | CoordinateLocation
  start_date: date = Field(description="The start date in the weather report's range")
  end_date: date = Field(description="The end date in the weather report's range")


type TripWeatherPlannerAgent = Agent[LocationWeatherRequest, bool]


async def create_meteorologist(
  model: str = GEMINI_25_FLASH,
) -> tuple[TripWeatherPlannerAgent, str, str]:
  bundle = await get_langfuse_prompt_bundle("climatologist")

  trip_weather_planner = Agent(
    model=create_litellm_model(model),
    instructions=bundle.instructions,
    deps_type=LocationWeatherRequest,
    output_type=bool,
    model_settings=bundle.model_settings,
    # mcp_servers=[sandboxed_python_mcp_server()],
    instrument=True,
  )

  @trip_weather_planner.tool_plain()
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
