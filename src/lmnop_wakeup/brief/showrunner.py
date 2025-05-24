# prompt = langfuse.get_prompt("showrunner", label="latest")


import asyncio
from datetime import date, datetime
from typing import TypedDict

from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent

from pirate_weather_api_client.models import Currently, Daily, Hourly

from ..common import get_hass_api_key
from ..llm import GEMINI_25_FLASH, create_litellm_model, get_langfuse_prompt_bundle
from ..locations import AddressLocation, CoordinateLocation
from ..schedule.timekeeper import EventRouteOptions
from ..tools import hass_api
from ..tools.calendar import gcalendar_api
from ..tools.calendar.model import Calendar, CalendarEvent


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
    model=create_litellm_model(model),
    instructions=bundle.instructions,
    deps_type=BriefingInputs,
    output_type=BriefingDetails,
    model_settings=bundle.model_settings,
    instrument=True,
  )

  return showrunner, bundle.instructions, bundle.task_prompt_templates


async def determine_day_schedule(
  showrunner: ShowrunnerAgent, deps: BriefingInputs
) -> BriefingDetails:
  logger.debug("Determining day schedule with Timekeeper agent")
  res = await showrunner.run("", deps=deps)
  logger.debug("Timekeeper agent run completed. Returning output.")
  return res.output
