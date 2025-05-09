# Alias the date types because we run into field name conflicts otherwise
from datetime import datetime as DateTime
from datetime import timedelta

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .common import TimeInfo
from .entity import ApiKey, EntityId

API_BASE = "http://home.don/api"


class CalendarEvent(BaseModel):
  summary: str
  start_ts: TimeInfo = Field(alias="start")
  end_ts: TimeInfo | None = Field(None, alias="end")
  description: str | None = None
  location: str | None = None

  def is_all_day(self) -> bool:
    return self.end_ts is None


class Calendar(BaseModel):
  entity_id: EntityId
  name: str
  todays_events: list[CalendarEvent] = []


class RestEndpoints:
  @staticmethod
  def calendars_endpoint() -> httpx.URL:
    return httpx.URL(f"{API_BASE}/calendars")

  @staticmethod
  def events_endpoint(calendar_id: EntityId, start: DateTime, end: DateTime) -> httpx.URL:
    return httpx.URL(
      f"{API_BASE}/calendars/{calendar_id}"
      f"?start={start.isoformat(timespec='seconds')}&end={end.isoformat(timespec='seconds')}"
    )


async def get_todays_calendar_events(hass_api_token: ApiKey):
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient(event_hooks={"request": []}) as client:
    cals_res = await client.get(
      RestEndpoints.calendars_endpoint(),
      headers=request_headers,
    )

    logger.info("calendars received. populating", calendars=cals_res.text)
    calendars = [Calendar.model_validate(raw_cal) for raw_cal in cals_res.json()]

    logger.info("requesting events")

    local_now = DateTime.now().astimezone()
    logger.debug("  now {ts}", ts=local_now.strftime("%H:%M:%S"))

    start_of_day = local_now.replace(hour=0, minute=0, second=0)
    logger.debug("start {ts}", ts=start_of_day.strftime("%H:%M:%S"))

    # We dip into the next day, because some events are nice to know about the day before
    end_of_day = local_now.replace(hour=8, minute=0, second=0) + timedelta(days=1)
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
