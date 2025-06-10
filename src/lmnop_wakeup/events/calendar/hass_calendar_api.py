from datetime import datetime as Datetime
from typing import NewType

import httpx
import structlog

from lmnop_wakeup.core.relative_dates import format_relative_date

from ...core.tracing import trace
from ...env import ApiKey
from ..model import Calendar, CalendarEvent

logger = structlog.get_logger()

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


@trace(name="api: hass.compute_route_durations")
async def calendar_events_in_range(
  briefing_date: Datetime,
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

      cal_events = []
      for i, raw_event in enumerate(events_res.json()):
        event_id = f"h{cal_idx}.{i}"
        cal_event = CalendarEvent.model_validate({**raw_event, "id": event_id})
        cal_event.when_colloquial = format_relative_date(
          briefing_date.date(), cal_event.start_datetime_aware
        )
        cal_events.append(cal_event)
      cal.events = cal_events

    return calendars
