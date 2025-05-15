from datetime import datetime

from langfuse import Langfuse
from pydantic import BaseModel
from pydantic_ai import Agent

from lmnop_wakeup.common import get_google_routes_api_key
from lmnop_wakeup.locations import Location
from lmnop_wakeup.tools import routes_api
from lmnop_wakeup.tools.routes_api import RouteDetailsByMode, TimeConstraint

from .llm import GEMINI_25_PRO, get_langfuse_prompt_bundle
from .tools.calendars import CalendarEvent


class SchedulingConcerns(BaseModel):
  pass


class SchedulingDetails(BaseModel):
  wakeup_time: datetime
  triggering_event_details: CalendarEvent | None


type TimekeeperAgent = Agent[SchedulingConcerns, SchedulingDetails]


async def create_timekeeper(model: str = GEMINI_25_PRO) -> TimekeeperAgent:
  bundle = await get_langfuse_prompt_bundle("timekeeper")

  timekeeper = Agent(
    instructions=bundle.instructions,
    deps_type=SchedulingConcerns,
    output_type=SchedulingDetails,
    model_settings=bundle.model_settings,
  )

  @timekeeper.tool_plain()
  async def compute_routes(
    from_location: Location,
    to_location: Location,
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

    Args:
      from_location: The starting point of the route.
      to_location: The destination point of the route.
      time_constraint: Specifies either a desired arrival time or a departure time.
      include_cycling: Whether to include cycling route details in the response.
      include_transit: Whether to include transit route details in the response.
      include_walking: Whether to include walking route details in the response.

    Returns:
      A RouteDetailsByMode object containing route information for the requested
      travel modes. This object includes details for driving (always included),
      and optionally for cycling, transit, and walking if requested.
    """
    return await routes_api.compute_route_durations(
      google_routes_api_key=get_google_routes_api_key(),
      origin=from_location,
      destination=to_location,
      time_constraint=time_constraint,
      include_cycling=include_cycling,
      include_transit=include_transit,
      include_walking=include_walking,
    )

  return timekeeper


async def determine_day_schedule(
  timekeeper: TimekeeperAgent, deps: SchedulingConcerns
) -> SchedulingDetails:
  res = await timekeeper.run("", deps=deps)
  return res.output


# Initialize Langfuse client
langfuse = Langfuse()


prompt = langfuse.get_prompt("timekeeper", label="latest")
