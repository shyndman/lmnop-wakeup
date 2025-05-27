from datetime import datetime as Datetime
from typing import NewType

import httpx
from loguru import logger

from ...env import ApiKey
from ..model import Calendar, CalendarEvent

_HASS_API_BASE = "http://home.don/api"

HassEntityId = NewType("HassEntityId", str)


class RestEndpoints:
  @staticmethod
  def calendars_endpoint() -> httpx.URL:
    return httpx.URL(f"{_HASS_API_BASE}/calendars")

  @staticmethod
  def events_endpoint(calendar_id: str, start: Datetime, end: Datetime) -> httpx.URL:
    return httpx.URL(
      f"{_HASS_API_BASE}/calendars/{calendar_id}"
      f"?start={start.isoformat(timespec='seconds')}&end={end.isoformat(timespec='seconds')}"
    )


async def calendar_events_in_range(
  start_ts: Datetime,
  end_ts: Datetime,
  hass_api_token: ApiKey,
) -> list[Calendar]:
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

    logger.info("requesting calendar events")
    for cal_idx, cal in enumerate(calendars):
      events_res = await client.get(
        RestEndpoints.events_endpoint(cal.entity_id, start_ts, end_ts),
        headers=request_headers,
      )

      cal_events = [
        CalendarEvent.model_validate({"entity_id": f"h{cal_idx}.{i}"}.update(raw_event))
        for i, raw_event in enumerate(events_res.json())
      ]
      cal.events = cal_events

    return calendars
