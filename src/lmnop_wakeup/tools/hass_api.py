from datetime import date, datetime
from typing import NewType, TypedDict

import httpx
from pydantic import BaseModel

from ..common import ApiKey

_HASS_API_BASE = "http://home.don/api"
HassEntityId = NewType("HassEntityId", str)


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


class EntityState(TypedDict):
  entity_id: HassEntityId
  last_changed: datetime
  last_updated: datetime
  state: str


async def get_entity_state(entity_id: HassEntityId, hass_api_token: ApiKey) -> EntityState:
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient(event_hooks={"request": []}) as client:
    res = await client.get(f"{_HASS_API_BASE}/states/{entity_id}", headers=request_headers)
    return res.json()
