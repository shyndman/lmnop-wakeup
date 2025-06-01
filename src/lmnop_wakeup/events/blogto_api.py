import re
from datetime import date, datetime, time, timedelta

import httpx
import rich
from pydantic import BaseModel, HttpUrl, field_validator
from pydantic.dataclasses import dataclass

from lmnop_wakeup.location.geocode_api import geocode_location

from ..core.cache import cached
from ..core.date import TimeInfo
from .calendar.gcalendar_api import (
  BLOGTO_CALENDAR_ID,
  CalendarEvent,
  get_calendar_event,
  insert_calendar_event,
  update_calendar_event,
)
from .event_summarizer_agent import EventSummarizerInput, get_event_summarizer_agent

BASE_URL = (
  "https://www.blogto.com/api/v2/events/?bundle_type=medium&date={date}&limit=9999&offset=0"
)


@dataclass
class BlogToListing:
  id: int
  name: str
  share_url: HttpUrl
  image_url: HttpUrl
  is_reviewed: bool
  date_reviewed: datetime | None


LOCAL_TZINFO = datetime.now().astimezone().tzinfo


class BlogToEvent(BaseModel):
  id: int
  title: str
  image_url: HttpUrl | None
  hub_page_image_url: HttpUrl | None
  share_url: HttpUrl | None
  description_stripped: str
  venue_name: str
  is_top_pick: bool
  date: date
  start_time: time
  end_time: time
  listing: BlogToListing | None

  @field_validator("image_url", "hub_page_image_url", "share_url", mode="before")
  @staticmethod
  def parse_empty_as_none(v):
    if isinstance(v, str) and v == "":
      return None
    return v

  @field_validator("start_time", "end_time", mode="before")
  @staticmethod
  def parse_time_string(v):
    if not isinstance(v, str):
      return v

    match = re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)", v.lower())
    if not match:
      return v

    hour, minute, period = match.groups()
    hour = int(hour)
    minute = int(minute)

    if period == "pm" and hour != 12:
      hour += 12
    elif period == "am" and hour == 12:
      hour = 0

    return time(hour, minute, tzinfo=LOCAL_TZINFO)


async def add_upcoming_blogto_events(day_count: int = 21) -> None:
  blogto_events = await fetch_upcoming_blogto_events(day_count)

  for bto_event in blogto_events:
    start = datetime.combine(bto_event.date, bto_event.start_time)
    end = datetime.combine(bto_event.date, bto_event.end_time)
    if end < start:
      end = end + timedelta(days=1)

    output = await get_event_summarizer_agent().run(
      EventSummarizerInput(
        description=bto_event.description_stripped,
      )
    )

    location = None
    if output.address:
      location = output.address
    elif bto_event.venue_name:
      location = bto_event.venue_name
    if location:
      results = await geocode_location(location)
      location = results[0].address if results else None

    event = CalendarEvent(
      id=str(bto_event.id),
      summary=bto_event.title,
      description=f"{output.summary}\n\n"
      f"audience: {output.intended_audience}\n"
      f"category: {output.category}\n"
      f"is top pick? {bto_event.is_top_pick}\n",
      start=TimeInfo(dateTime=start),
      end=TimeInfo(dateTime=end),
      location=location,
      source_url=str(bto_event.share_url),
      extended_properties={
        "private": {
          "blogto_event": bto_event.model_dump_json(),
          "intended_audience": output.intended_audience,
          "is_top_pick": bto_event.is_top_pick,
          "category": output.category,
        },
      },
    )

    maybe_event = get_calendar_event(BLOGTO_CALENDAR_ID, str(bto_event.id))
    if maybe_event:
      rich.print(f"Event {bto_event.id} already exists in calendar, updating.")
      update_calendar_event(calendar_id=BLOGTO_CALENDAR_ID, event=event)
    else:
      rich.print(event)
      insert_calendar_event(calendar_id=BLOGTO_CALENDAR_ID, event=event)


@cached(ttl=60 * 60 * 12)
async def fetch_upcoming_blogto_events(day_count):
  start = date.today()
  blogto_events: list[BlogToEvent] = []
  async with httpx.AsyncClient() as client:
    for day in range(day_count):
      dt = start + timedelta(days=day)
      url = BASE_URL.format(date=dt.isoformat())
      res = await client.get(url)
      json = res.json()
      blogto_events.extend(BlogToEvent.model_validate({"date": dt, **e}) for e in json["results"])
  return blogto_events
