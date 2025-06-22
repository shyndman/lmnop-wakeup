from datetime import datetime

import structlog
from googleapiclient.discovery import build

from lmnop_wakeup.core.relative_dates import format_relative_date

from ...core.tracing import trace_sync
from ...tools.google_auth import authenticate
from ..model import Calendar, CalendarEvent

logger = structlog.get_logger()


BIRTHDAY_CALENDAR_ID = "md3ntu1lbq9vqc59fs75svbusg@group.calendar.google.com"
BLOGTO_CALENDAR_ID = (
  "78a50bde5c29851a307180b7743c529df2a3a656502100e7c8a19bfdeceb326c@group.calendar.google.com"
)
HILARY_CALENDAR_ID = "hilary.hacksel@gmail.com"
PERSONAL_CALENDAR_ID = "primary"  # "scotty.hyndman@gmail.com"
SHARED_CALENDAR_ID = "family16125668672800183011@group.calendar.google.com"
CALENDAR_IDS = [
  BIRTHDAY_CALENDAR_ID,
  BLOGTO_CALENDAR_ID,
  HILARY_CALENDAR_ID,
  PERSONAL_CALENDAR_ID,
  SHARED_CALENDAR_ID,
]

# This does not appear in CALENDAR_IDS, because these are workflow outputs, not inputs
AUTOMATION_SCHEDULER_CALENDAR_ID = (
  "afcafa68dfd547f5076ef90ee75df884da1324cabfa2caded5c0abe95d7bccfd@group.calendar.google.com"
)


def get_services():
  service = build("calendar", "v3", credentials=authenticate())
  return service.calendars(), service.events()


@trace_sync(name="api: gcal.compute_route_durations")
def calendar_events_in_range(
  briefing_date: datetime, start_ts: datetime, end_ts: datetime
) -> list[Calendar]:
  calendars_service, events_service = get_services()
  cal_ents = [calendars_service.get(calendarId=id).execute() for id in CALENDAR_IDS]
  calendars = [
    Calendar(
      entity_id=cal_ent.get("id"),
      name=cal_ent.get("summary"),
    )
    for cal_ent in cal_ents
  ]

  for cal_idx, calendar in enumerate(calendars):
    res = events_service.list(
      calendarId=calendar.entity_id,
      timeMin=start_ts.isoformat(),
      timeMax=end_ts.isoformat(),
      maxResults=2500,
      singleEvents=True,
      orderBy="startTime",
    ).execute()

    events = res.get("items", [])
    if not events:
      logger.debug("No upcoming events found.")
      continue

    cal_events = [
      CalendarEvent.model_validate({**raw_event, "id": f"g{cal_idx}.{i}"})
      for i, raw_event in enumerate(events)
    ]
    for cal_event in cal_events:
      cal_event.when_colloquial = format_relative_date(
        briefing_date.date(), cal_event.start_datetime_aware
      )
    calendar.events = cal_events

  return calendars


def get_calendar_event(calendar_id: str, event_id: str) -> CalendarEvent | None:
  _, events_service = get_services()
  try:
    event = events_service.get(calendarId=calendar_id, eventId=event_id).execute()
    return CalendarEvent.model_validate(event)
  except Exception as e:
    logger.error(f"Failed to retrieve event {event_id} from calendar {calendar_id}: {e}")
    return None


def insert_calendar_event(calendar_id: str, event: CalendarEvent):
  _, events_service = get_services()
  event = events_service.insert(
    calendarId=calendar_id,
    body=event.model_dump(mode="json"),
  ).execute()


def update_calendar_event(calendar_id: str, event: CalendarEvent):
  _, events_service = get_services()
  event = events_service.update(
    calendarId=calendar_id,
    eventId=event.id,
    body=event.model_dump(),
  ).execute()
