from datetime import date, datetime
from datetime import datetime as Datetime
from typing import NewType, TypedDict

import httpx
from loguru import logger
from pydantic import BaseModel

from ..common import ApiKey
from .calendar.model import Calendar, CalendarEvent

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
  start_ts: datetime,
  end_ts: datetime,
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
    for cal in calendars:
      events_res = await client.get(
        RestEndpoints.events_endpoint(cal.entity_id, start_ts, end_ts),
        headers=request_headers,
      )

      cal_events = [CalendarEvent.model_validate(raw_event) for raw_event in events_res.json()]
      cal.events = cal_events

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
