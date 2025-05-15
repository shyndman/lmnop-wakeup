import os.path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from lmnop_wakeup.common import Calendar, CalendarEvent

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


SHARED_CALENDAR_ID = "family16125668672800183011@group.calendar.google.com"


def get_calendar_events_in_range(from_ts: datetime, until_ts: datetime):
  service = build("calendar", "v3", credentials=authenticate())
  res = (
    service.events()
    .list(
      calendarId=SHARED_CALENDAR_ID,
      timeMin=from_ts,
      timeMax=until_ts,
      singleEvents=True,
      orderBy="startTime",
      maxResults=2500,
    )
    .execute()
  )

  calendar = Calendar(
    entity_id=SHARED_CALENDAR_ID,
    name=res.get("description"),
    events=[],
  )

  events = res.get("items", [])
  if not events:
    print("No upcoming events found.")
    return calendar

  calendar.events.append(
    *map(lambda e: CalendarEvent.model_validate(e), events),
  )
  return calendar


def authenticate():
  """Returns calendar credentials, sending the user to SSO if required"""

  credentials = None

  # The file token.json stores the user's access and refresh tokens, and is created automatically
  # when the authorization flow completes for the first time.
  if os.path.exists(".google/token.json"):
    credentials = Credentials.from_authorized_user_file(".google/token.json", SCOPES)

  # No valid credentials available, let the user log in.
  if not credentials or not credentials.valid:
    if credentials and credentials.expired and credentials.refresh_token:
      credentials.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(".google/credentials.json", SCOPES)
      credentials = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open(".google/token.json", "w") as token:
      token.write(credentials.to_json())

  return credentials
