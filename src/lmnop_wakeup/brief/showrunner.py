# prompt = langfuse.get_prompt("showrunner", label="latest")


import asyncio
from datetime import date, datetime
from typing import TypedDict

from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent

from lmnop_wakeup.llm import GEMINI_25_FLASH, get_langfuse_prompt_bundle
from lmnop_wakeup.locations import AddressLocation, CoordinateLocation
from lmnop_wakeup.schedule.timekeeper import EventRouteOptions
from lmnop_wakeup.tools import routes_api
from lmnop_wakeup.tools.routes_api import RouteDetailsByMode, TimeConstraint
from pirate_weather_api_client.models import Currently, Daily, Hourly

from ..common import Calendar, CalendarEvent, get_google_routes_api_key, get_hass_api_key
from ..tools import gcalendar_api, hass_api


async def calendar_events_for_briefing(start_ts: datetime, end_ts: datetime) -> list[Calendar]:
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


class BriefingInputs(TypedDict):
  calendars: list[Calendar]
  todays_date: date
  is_today_workday: bool

  current_weather: Currently
  hourly_weather: Hourly
  daily_weather: Daily

  home_location: AddressLocation | CoordinateLocation


class BriefingDetails(BaseModel):
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


type ShowrunnerAgent = Agent[BriefingInputs, BriefingDetails]


async def create_showrunner(model: str = GEMINI_25_FLASH) -> tuple[ShowrunnerAgent, str, str]:
  logger.debug("Creating Timekeeper agent with model: {model}", model=model)
  bundle = await get_langfuse_prompt_bundle("showrunner")
  showrunner = Agent(
    model=model,
    instructions=bundle.instructions,
    deps_type=BriefingInputs,
    output_type=BriefingDetails,
    model_settings=bundle.model_settings,
    instrument=True,
  )

  @showrunner.tool_plain()
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

  return showrunner, bundle.instructions, bundle.task_prompt_templates


async def determine_day_schedule(
  showrunner: ShowrunnerAgent, deps: BriefingInputs
) -> BriefingDetails:
  logger.debug("Determining day schedule with Timekeeper agent")
  res = await showrunner.run("", deps=deps)
  logger.debug("Timekeeper agent run completed. Returning output.")
  return res.output
