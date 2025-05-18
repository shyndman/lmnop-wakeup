import asyncio
from datetime import date, datetime
from typing import TypedDict

from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from pirate_weather_api_client.models import HourlyDataItem

from ..common import Calendar, CalendarEvent, get_google_routes_api_key, get_hass_api_key
from ..llm import GEMINI_25_FLASH, get_langfuse_prompt_bundle
from ..locations import AddressLocation, CoordinateLocation
from ..tools import gcalendar_api, hass_api, routes_api
from ..tools.routes_api import (
  CyclingRouteDetails,
  RouteDetails,
  RouteDetailsByMode,
  TimeConstraint,
)


async def calendar_events_for_scheduling(start_ts: datetime, end_ts: datetime) -> list[Calendar]:
  hass_calendars_task = hass_api.calendar_events_in_range(
    start_ts=start_ts,
    end_ts=end_ts,
    hass_api_token=get_hass_api_key(),
  )

  loop = asyncio.get_running_loop()
  shared_calendar_task = loop.run_in_executor(
    None,
    lambda: gcalendar_api.calendar_events_in_range(
      start_ts=start_ts,
      end_ts=end_ts,
    ),
  )

  hass_calendars, google_calendars = await asyncio.gather(
    hass_calendars_task,
    shared_calendar_task,
  )

  return [] + google_calendars + hass_calendars


class SchedulingInputs(TypedDict):
  calendars: list[Calendar]
  todays_date: date
  is_today_workday: bool
  hourly_weather: list[HourlyDataItem]
  home_location: AddressLocation | CoordinateLocation


class ModeRejectionResult(BaseModel):
  """A data structure representing an LLM's rationale for rejecting a particular transportation
  mode.

  Attributes:
    rejection_rationale (str): A human-readable explanation for why a specific
      transportation mode was deemed unsuitable by the LLM.
  """

  rejection_rationale: str
  """Two sentences max, specifically describing the broken rule that lead to the rejection"""


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
  triggering_event_details: CalendarEvent | None
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
    origin: AddressLocation | CoordinateLocation,
    destination: AddressLocation | CoordinateLocation,
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

    logger.debug(
      "Timekeeper tool called: compute_routes with origin={origin}, "
      "destination={destination}, "
      "time_constraint={time_constraint}, include_cycling={include_cycling}, "
      "include_transit={include_transit}, include_walking={include_walking}",
      origin=origin,
      destination=destination,
      time_constraint=time_constraint,
      include_cycling=include_cycling,
      include_transit=include_transit,
      include_walking=include_walking,
    )
    return await routes_api.compute_route_durations(
      google_routes_api_key=get_google_routes_api_key(),
      origin=origin,
      destination=destination,
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
