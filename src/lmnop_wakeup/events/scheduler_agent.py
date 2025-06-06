import textwrap
from datetime import datetime
from typing import override

import structlog
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from ..llm import (
  LangfuseAgentInput,
  LmnopAgent,
  ModelName,
  extract_pydantic_ai_callback,
)
from ..location import routes_api
from ..location.model import CoordinateLocation
from ..location.routes_api import (
  RouteDetailsByMode,
  TimeConstraint,
)
from .model import CalendarsOfInterest, Schedule

logger = structlog.get_logger()


class SchedulerInput(LangfuseAgentInput):
  """Input data required by the Timekeeper LLM to determine optimal wake-up times and schedules.

  This class encapsulates all the contextual information needed for the scheduling agent
  to make intelligent decisions about when a user should wake up, considering their
  calendar events, weather conditions, work schedule, and location.
  """

  scheduling_date: datetime
  """Midnight of the current date for which the schedule is being computed. The timezone is
  associated with this datetime is local time."""

  home_location: CoordinateLocation
  """The user's home location, used as the origin point for route calculations."""

  calendars: CalendarsOfInterest
  """Collection of calendar events on the briefing day from various sources that may influence the
  schedule."""

  hourly_weather_api_result: str
  """Hourly weather forecast data that may impact transportation mode decisions and timing."""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    return {
      "scheduling_date": textwrap.dedent(f"""
        {self.scheduling_date.strftime("%A, %B %d, %Y")}
        iso8601 format: {self.scheduling_date.isoformat()}
        """).lstrip(),
      "home_location": self.home_location.model_dump_json(indent=4),
      "calendars_of_interest": self.calendars.model_dump_markdown(self.scheduling_date),
      "hourly_weather": self.hourly_weather_api_result,
    }


class SchedulerOutput(BaseModel):
  """Represents the detailed schedule and route information determined by the Timekeeper LLM.

  This structure provides the necessary context for the user to understand the planned wake-up
  time, the event that influenced it, and the computed travel routes for the day.
  """

  schedule: Schedule


type SchedulerAgent = LmnopAgent[SchedulerInput, SchedulerOutput]


def get_scheduler_agent(config: RunnableConfig) -> SchedulerAgent:
  """Get the location resolver agent."""

  agent = LmnopAgent[SchedulerInput, SchedulerOutput].create(
    "scheduler",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=SchedulerInput,
    output_type=SchedulerOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  @agent.tool_plain()
  async def compute_routes(
    origin: CoordinateLocation,
    destination: CoordinateLocation,
    time_constraint: TimeConstraint,
    include_cycling: bool,
    include_transit: bool,
    include_walking: bool,
  ) -> RouteDetailsByMode:
    """
    Computes route details between two locations for various travel modes.

    This function calculates estimated travel times, distances, and other route
    information based on the provided origin, destination, time constraints,
    and desired travel modes. It utilizes the Google Routes API internally.

    Note: Because these routes are so often being calculated between home and
    some other place, a "home" location object is provided in the prompt that
    can be used to represent an origin or destination.

    Args:
      origin: The starting point of the route. Can be an `AddressLocation`, a `CoordinateLocation`,
          and less frequently, a `NamedLocation`.
      destination: The destination point of the route. Can be an `AddressLocation`, a
          `CoordinateLocation`, and less frequently, a `NamedLocation`.
      time_constraint: Specifies either a desired arrival time or a departure time.
      include_cycling: Whether to include cycling route details in the response.
      include_transit: Whether to include transit route details in the response.
      include_walking: Whether to include walking route details in the response.

    Returns:
      A RouteDetailsByMode object containing route information for the requested
      travel modes. This object includes details for driving (always included),
      and optionally for cycling, transit, and walking if requested.
    """

    logger.info(
      f"Timekeeper tool called: compute_routes with origin={origin}, "
      f"destination={destination}, "
      f"time_constraint={time_constraint}, include_cycling={include_cycling}, "
      f"include_transit={include_transit}, include_walking={include_walking}"
    )
    return await routes_api.compute_route_durations(
      origin=origin,
      destination=destination,
      time_constraint=time_constraint,
      include_cycling=include_cycling,
      include_transit=include_transit,
      include_walking=include_walking,
    )

  return agent
