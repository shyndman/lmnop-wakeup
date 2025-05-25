import asyncio
from datetime import date, datetime, timedelta
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.func import entrypoint, task
from loguru import logger
from pydantic import AwareDatetime, BaseModel

from lmnop_wakeup.tools.weather_api import WeatherReport, get_weather_report

from ..common import get_hass_api_key, get_pirate_weather_api_key
from ..locations import AddressLocation, CoordinateLocation
from ..schedule.timekeeper import SchedulingDetails
from ..tools.calendar.model import Calendar
from ..tools.calendars import get_filtered_calendars_with_notes
from ..tools.hass_api import GeneralInfo, HassEntityId, get_entity_state
from ..utils.date import end_of_local_day, start_of_local_day
from ..utils.logging import rich_sprint


class MorningBriefing(TypedDict):
  # produced_at: datetime
  # announcment_date: datetime
  pass


class BriefingScript(BaseModel):
  pass


class BriefingInputs(TypedDict):
  briefing_date: date
  location: CoordinateLocation | AddressLocation
  schedule: SchedulingDetails
  previous_briefings: list[MorningBriefing]


@task()
async def get_weather_reports():
  pass


@task()
async def _get_general_information(
  todays_date: date = datetime.now().astimezone().date(),
) -> GeneralInfo:
  workday_entity = await get_entity_state(
    HassEntityId("binary_sensor.is_today_a_workday"),
    get_hass_api_key(),
  )
  return GeneralInfo(
    todays_date=todays_date,
    is_today_workday=workday_entity["state"] == "on",
  )


EVENT_CONSIDERATION_SPAN = timedelta(days=21)


@task()
async def _get_calendars(briefing_date: date) -> list[Calendar]:
  start_of_day = start_of_local_day(briefing_date)
  end_of_day = end_of_local_day(briefing_date)
  # We get the previous day's events so the agent can quip about any late nights
  start_of_span = start_of_day - timedelta(days=1)
  end_of_span = end_of_day + EVENT_CONSIDERATION_SPAN

  calendars = await get_filtered_calendars_with_notes(
    start_ts=start_of_span,
    end_ts=end_of_span,
    hass_api_token=get_hass_api_key(),
  )
  return calendars


@task()
async def _get_weather_report(
  location: CoordinateLocation, report_start_time: AwareDatetime
) -> WeatherReport:
  return await get_weather_report(
    location,
    report_start_time=report_start_time,
    pirate_weather_api_key=get_pirate_weather_api_key(),
  )


@entrypoint(checkpointer=MemorySaver())
async def _start_briefing_workflow(schedule: BriefingInputs) -> MorningBriefing:
  # Collect the information we need:
  day = schedule["briefing_date"]
  start_of_day = start_of_local_day(day)
  end_of_day = end_of_local_day(day)
  end_of_span = end_of_day + EVENT_CONSIDERATION_SPAN
  location = schedule["location"]

  general_info, calendars, weather_report = await asyncio.gather(
    _get_general_information(todays_date=day),
    _get_calendars(start_ts=start_of_day, end_ts=end_of_span),
    _get_weather_report(location=location, report_start_time=start_of_day),
  )

  # - weather report for home
  # - calendars
  # - schedule
  # - previous briefings

  # is_approved = interrupt({} # Any JSON-serializable here)
  return MorningBriefing()


async def run(scheduling_details: SchedulingDetails) -> None:
  briefing_date = scheduling_details.date
  config: RunnableConfig = {"configurable": {"thread_id": briefing_date.isoformat}}
  result = await _start_briefing_workflow.ainvoke(briefing_date, config)
  logger.info("Briefing result:\n\n{result}", result=rich_sprint(result))
