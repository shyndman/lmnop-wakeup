from datetime import datetime
from typing import Any, NewType

import httpx
from pydantic import BaseModel

from .common import ApiKey

EntityId = NewType("EntityId", str)


class EntityState(BaseModel):
  entity_id: EntityId
  last_changed: datetime
  last_updated: datetime
  state: str


API_BASE = "http://home.don/api"


async def get_entity_state(hass_api_token: ApiKey, entity_id: EntityId) -> Any:
  request_headers = {
    "Authorization": f"Bearer {hass_api_token}",
    "Content-Type": "application/json",
  }
  async with httpx.AsyncClient(event_hooks={"request": []}) as client:
    res = await client.get(f"{API_BASE}/states/{entity_id}", headers=request_headers)
    return res.json()
