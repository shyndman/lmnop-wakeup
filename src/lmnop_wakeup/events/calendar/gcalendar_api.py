import os.path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from ...core.tracing import trace_sync
from ..model import Calendar, CalendarEvent

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


BIRTHDAY_CALENDAR_ID = "md3ntu1lbq9vqc59fs75svbusg@group.calendar.google.com"
PERSONAL_CALENDAR_ID = "primary"  # "scotty.hyndman@gmail.com"
SHARED_CALENDAR_ID = "family16125668672800183011@group.calendar.google.com"
CALENDAR_IDS = [
  PERSONAL_CALENDAR_ID,
  BIRTHDAY_CALENDAR_ID,
  SHARED_CALENDAR_ID,
]


@trace_sync(name="api: gcal.compute_route_durations")
def calendar_events_in_range(start_ts: datetime, end_ts: datetime) -> list[Calendar]:
  service = build("calendar", "v3", credentials=authenticate())
  calendars_service = service.calendars()
  cal_ents = [calendars_service.get(calendarId=id).execute() for id in CALENDAR_IDS]
  calendars = [
    Calendar(
      entity_id=cal_ent.get("id"),
      name=cal_ent.get("summary"),
    )
    for cal_ent in cal_ents
  ]

  for cal_idx, calendar in enumerate(calendars):
    res = (
      service.events()
      .list(
        calendarId=calendar.entity_id,
        timeMin=start_ts.isoformat(),
        timeMax=end_ts.isoformat(),
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime",
      )
      .execute()
    )

    events = res.get("items", [])
    if not events:
      logger.debug("No upcoming events found.")
      continue

    cal_events = [
      CalendarEvent.model_validate({**raw_event, "event_id": f"g{cal_idx}.{i}"})
      for i, raw_event in enumerate(events)
    ]
    calendar.events = cal_events

  return calendars


def authenticate():
  """Returns calendar credentials, sending the user to SSO if required"""

  credentials = None

  # The file token.json stores the user's access and refresh tokens, and is created automatically
  # when the authorization flow completes for the first time.
  if os.path.exists(".google/token.json"):
    logger.debug("Loading credentials from token.json")
    credentials = Credentials.from_authorized_user_file(".google/token.json", SCOPES)
  else:
    logger.warning(
      "No token.json file found. Please run the script to authenticate with Google Calendar API.",
    )

  # No valid credentials available, let the user log in.
  if not credentials or not credentials.valid:
    try:
      if credentials and credentials.expired and credentials.refresh_token:
        logger.debug("Refreshing expired credentials")
        credentials.refresh(Request())
    except Exception:
      credentials = None
      logger.exception("Failed to refresh credentials, requesting new ones")

    if not credentials or not credentials.valid:
      logger.debug("No valid credentials, requesting new ones")
      flow = InstalledAppFlow.from_client_secrets_file(".google/credentials.json", SCOPES)
      credentials = flow.run_local_server(port=0)

    # Save the credentials for the next run
    logger.debug("Saving credentials to token.json")
    with open(".google/token.json", "w") as token:
      token.write(credentials.to_json())

  return credentials
