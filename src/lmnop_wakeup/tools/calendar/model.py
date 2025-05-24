from pydantic import BaseModel, EmailStr, Field
from pydantic_extra_types.timezone_name import TimeZoneName

from lmnop_wakeup.utils.date import TimeInfo


class CalendarEmailUser(BaseModel):
  email: EmailStr


class CalendarUser(CalendarEmailUser):
  display_name: str = Field(alias="displayName")
  email: EmailStr


class CalendarEvent(BaseModel):
  summary: str
  creator: CalendarEmailUser | None = None
  attendees: list[CalendarUser] | None = None
  start_ts: TimeInfo = Field(alias="start")
  end_ts: TimeInfo | None = Field(None, alias="end")
  description: str | None = None
  location: str | None = None

  def is_all_day(self) -> bool:
    return self.end_ts is None


class Calendar(BaseModel):
  entity_id: str
  name: str
  events: list[CalendarEvent] = []
  time_zone: TimeZoneName | None = None
  notes_for_processing: str | None = None
