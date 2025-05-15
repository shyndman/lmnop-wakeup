# Alias the date types because we run into field name conflicts otherwise
from datetime import date, time, timedelta
from datetime import date as Date
from datetime import datetime as DateTime
from typing import override

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .hass_api import ApiKey, HassEntityId

API_BASE = "http://home.don/api"


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


class CalendarEvent(BaseModel):
  summary: str
  start_ts: TimeInfo = Field(alias="start")
  end_ts: TimeInfo | None = Field(None, alias="end")
  description: str | None = None
  location: str | None = None

  def is_all_day(self) -> bool:
    return self.end_ts is None


class Calendar(BaseModel):
  entity_id: HassEntityId
  name: str
  todays_events: list[CalendarEvent] = []


class RestEndpoints:
  @staticmethod
  def calendars_endpoint() -> httpx.URL:
    return httpx.URL(f"{API_BASE}/calendars")

  @staticmethod
  def events_endpoint(calendar_id: HassEntityId, start: DateTime, end: DateTime) -> httpx.URL:
    return httpx.URL(
      f"{API_BASE}/calendars/{calendar_id}"
      f"?start={start.isoformat(timespec='seconds')}&end={end.isoformat(timespec='seconds')}"
    )


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
    calendars = [Calendar.model_validate(raw_cal) for raw_cal in cals_res.json()]

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

      cal_events = [CalendarEvent.model_validate(raw_event) for raw_event in events_res.json()]
      cal.todays_events = cal_events
      logger.debug("  → {cal}: today's events ✓ ({count})", cal=cal.name, count=len(cal_events))

    return calendars
