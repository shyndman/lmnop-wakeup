from datetime import date, datetime, time, timedelta
from datetime import date as Date
from datetime import datetime as DateTime
from typing import NewType, TypedDict, override

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from ..common import ApiKey

_HASS_API_BASE = "http://home.don/api"
HassEntityId = NewType("HassEntityId", str)


class TimeInfo(BaseModel):
  date: Date | None = None
  dateTime: DateTime | None = None

  # Validate that one and only one is provided
  @override
  def model_post_init(self, __context):
    if (self.date is None and self.dateTime is None) or (
      self.date is not None and self.dateTime is not None
    ):
      raise ValueError("Either 'date' or 'dateTime' must be provided, but not both")


class HassCalendarEvent(BaseModel):
  summary: str
  start_ts: TimeInfo = Field(alias="start")
  end_ts: TimeInfo | None = Field(None, alias="end")
  description: str | None = None
  location: str | None = None

  def is_all_day(self) -> bool:
    return self.end_ts is None


class HassCalendar(BaseModel):
  entity_id: HassEntityId
  name: str
  todays_events: list[HassCalendarEvent] = []


class RestEndpoints:
  @staticmethod
  def calendars_endpoint() -> httpx.URL:
    return httpx.URL(f"{_HASS_API_BASE}/calendars")

  @staticmethod
  def events_endpoint(calendar_id: HassEntityId, start: DateTime, end: DateTime) -> httpx.URL:
    return httpx.URL(
      f"{_HASS_API_BASE}/calendars/{calendar_id}"
      f"?start={start.isoformat(timespec='seconds')}&end={end.isoformat(timespec='seconds')}"
    )


async def get_calendar_events_in_range(
  from_ts: datetime,
  until_ts: datetime,
  hass_api_token: ApiKey,
) -> list[HassCalendar]:
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient() as client:
    cals_res = await client.get(
      RestEndpoints.calendars_endpoint(),
      headers=request_headers,
    )

    logger.info("calendars received. populating", calendars=cals_res.text)
    calendars = [HassCalendar.model_validate(raw_cal) for raw_cal in cals_res.json()]

    logger.info("requesting calendar events")
    for cal in calendars:
      events_res = await client.get(
        RestEndpoints.events_endpoint(cal.entity_id, from_ts, until_ts),
        headers=request_headers,
      )

      cal_events = [HassCalendarEvent.model_validate(raw_event) for raw_event in events_res.json()]
      cal.todays_events = cal_events

    return calendars


async def get_relevant_calendar_events(
  today_override: date | None,
  hass_api_token: ApiKey,
):
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient() as client:
    cals_res = await client.get(
      RestEndpoints.calendars_endpoint(),
      headers=request_headers,
    )

    logger.info("calendars received. populating", calendars=cals_res.text)
    calendars = [HassCalendar.model_validate(raw_cal) for raw_cal in cals_res.json()]

    logger.info("requesting events")

    today = None
    if today_override is not None:
      today = DateTime.combine(today_override, time(hour=9, minute=0, second=0))
    else:
      today = today_override or DateTime.now().astimezone()

    logger.debug("  now {ts}", ts=today.strftime("%H:%M:%S"))

    start_of_day = today.replace(hour=0, minute=0, second=0)
    logger.debug("start {ts}", ts=start_of_day.strftime("%H:%M:%S"))

    # We dip into the next day, because some events are nice to know about the day before
    end_of_day = today.replace(hour=8, minute=0, second=0) + timedelta(days=1)
    logger.debug("  end {ts}", ts=end_of_day.strftime("%H:%M:%S"))

    for cal in calendars:
      events_res = await client.get(
        RestEndpoints.events_endpoint(cal.entity_id, start_of_day, end_of_day),
        headers=request_headers,
      )

      cal_events = [HassCalendarEvent.model_validate(raw_event) for raw_event in events_res.json()]
      cal.todays_events = cal_events
      logger.debug("  → {cal}: today's events ✓ ({count})", cal=cal.name, count=len(cal_events))

    return calendars


class EntityState(TypedDict):
  entity_id: HassEntityId
  last_changed: datetime
  last_updated: datetime
  state: str


class GeneralInfo(BaseModel):
  todays_date: date
  is_today_workday: bool


async def get_general_information(
  hass_api_token: ApiKey,
  todays_date: date = datetime.now().astimezone().date(),
):
  workday_entity = await get_entity_state(
    HassEntityId("binary_sensor.is_today_a_workday"),
    hass_api_token,
  )
  return GeneralInfo(
    todays_date=todays_date,
    is_today_workday=workday_entity["state"] == "on",
  )


async def get_entity_state(entity_id: HassEntityId, hass_api_token: ApiKey) -> EntityState:
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient(event_hooks={"request": []}) as client:
    res = await client.get(f"{_HASS_API_BASE}/states/{entity_id}", headers=request_headers)
    return res.json()
