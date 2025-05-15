from datetime import date, datetime
from enum import StrEnum
from typing import TypedDict

from langfuse import Langfuse
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from lmnop_wakeup.common import get_google_routes_api_key
from lmnop_wakeup.locations import AddressLocation, CoordinateLocation, Location
from lmnop_wakeup.tools import routes_api
from lmnop_wakeup.tools.routes_api import (
  CyclingRouteDetails,
  RouteDetails,
  RouteDetailsByMode,
  TimeConstraint,
)
from pirate_weather_api_client.models import HourlyDataItem

from .llm import GEMINI_25_FLASH, get_langfuse_prompt_bundle
from .tools.hass_api import HassCalendar, HassCalendarEvent

# 1. HOUSEHOLD INFORMATION:
logger.info("Initializing scheduler")
#    - Home address
#    - Household members (Scott and Hilary)
#    - Preparation times and wake-up constraints

# 2. CALENDAR DATA:
#    - Multiple calendars, each with a description_for_llm indicating owner and purpose
#    - Events containing:
#      * event_id: Unique identifier
#      * summary: Event title/name
#      * description: Detailed description (may contain keywords for transportation eligibility)
#      * location: Physical address or indication of home-based event
#      * event_start_ts: Start time in ISO8601 format
#      * event_end_ts: End time in ISO8601 format
#      * calendar_id: Identifier of the calendar this event belongs to

# 3. TIME & DATE CONTEXT:
#    - today_date: Current date
#    - day_of_week: Current day (to determine weekday vs weekend for wake-up time)

# 4. WEATHER INFORMATION:
#    - Hourly weather data for today with conditions (needed for walking/biking eligibility)


class WeekDay(StrEnum):
  monday = "Monday"
  tuesday = "Tuesday"
  wednesday = "Wednesday"
  thursday = "Thursday"
  friday = "Friday"
  saturday = "Saturday"
  sunday = "Sunday"


WEEK_DAY_MAPPING = {
  0: WeekDay.monday,
  1: WeekDay.tuesday,
  2: WeekDay.wednesday,
  3: WeekDay.thursday,
  4: WeekDay.friday,
  5: WeekDay.saturday,
  6: WeekDay.sunday,
}


class SchedulingInputs(TypedDict):
  calendars: list[HassCalendar]
  todays_date: date
  is_today_workday: bool
  hourly_weather: list[HourlyDataItem]
  home_location: Location


class ModeRejectionResult(BaseModel):
  """A data structure representing an LLM's rationale for rejecting a particular transportation
  mode.

  Attributes:
    rejection_rationale (str): A human-readable explanation for why a specific
      transportation mode was deemed unsuitable by the LLM.
  """

  rejection_rationale: str
  """A sentence on why this mode was rejected"""


class EventRouteOptions(BaseModel):
  """Represents the available route options and details for travel between two locations.

  This structure is used by the Timekeeper LLM to understand the possible ways to travel
  for a scheduled event, including details for different transportation modes and
  reasons why a mode might be unsuitable.
  """

  origin: AddressLocation | CoordinateLocation
  """The starting location for the route."""
  destination: AddressLocation | CoordinateLocation
  """The ending location for the route."""
  related_event_id: list[str] = Field(min_length=1, max_length=2)
  """The identifier(s) of the calendar event(s) the user is travelling to or from, or both"""

  bike: CyclingRouteDetails | ModeRejectionResult
  """Route details for cycling, or a rejection result if cycling is not a viable option."""
  drive: RouteDetails
  """Route details for driving. A driving route is always expected to be available."""
  transit: RouteDetails | ModeRejectionResult
  """Route details for public transit, or a rejection result if transit is not a viable option."""
  walk: RouteDetails | ModeRejectionResult
  """Route details for walking, or a rejection result if walking is not a viable option."""


class SchedulingDetails(BaseModel):
  """Represents the detailed schedule and route information determined by the Timekeeper LLM.

  This structure provides the necessary context for the user to understand the planned wake-up
  time, the event that influenced it, and the computed travel routes for the day.
  """

  wakeup_time: datetime
  """The calculated time the user should wake up."""
  triggering_event_details: HassCalendarEvent | None
  """The calendar event that was used to determine the wakeup_time. This will be `null` if the
  wake-up time was based on the latest possible time rather than a specific event."""
  routes: list[EventRouteOptions]
  """Details about the computed routes for travel related to the scheduled event(s)."""


type TimekeeperAgent = Agent[SchedulingInputs, SchedulingDetails]


async def create_timekeeper(model: str = GEMINI_25_FLASH) -> tuple[TimekeeperAgent, str, str]:
  logger.debug("Creating Timekeeper agent with model: {model}", model=model)
  bundle = await get_langfuse_prompt_bundle("timekeeper")
  timekeeper = Agent(
    model=model,
    instructions=bundle.instructions,
    deps_type=SchedulingInputs,
    output_type=SchedulingDetails,
    model_settings=bundle.model_settings,
    instrument=True,
  )

  @timekeeper.tool_plain()
  async def compute_routes(
    from_location: AddressLocation | CoordinateLocation,
    to_location: AddressLocation | CoordinateLocation,
    time_constraint: TimeConstraint,
    include_cycling: bool,
    include_transit: bool,
    include_walking: bool,
  ) -> RouteDetailsByMode:
    logger.debug(
      "Timekeeper tool called: compute_routes with from_location={from_location}, "
      "to_location={to_location}, "
      "time_constraint={time_constraint}, include_cycling={include_cycling}, "
      "include_transit={include_transit}, include_walking={include_walking}",
      from_location=from_location,
      to_location=to_location,
      time_constraint=time_constraint,
      include_cycling=include_cycling,
      include_transit=include_transit,
      include_walking=include_walking,
    )
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

  return timekeeper, bundle.instructions, bundle.task_prompt_templates


async def determine_day_schedule(
  timekeeper: TimekeeperAgent, deps: SchedulingInputs
) -> SchedulingDetails:
  logger.debug("Determining day schedule with Timekeeper agent")
  res = await timekeeper.run("", deps=deps)
  logger.debug("Timekeeper agent run completed. Returning output.")
  return res.output


# Initialize Langfuse client
langfuse = Langfuse()
logger.debug("Langfuse client initialized")


prompt = langfuse.get_prompt("timekeeper", label="latest")
