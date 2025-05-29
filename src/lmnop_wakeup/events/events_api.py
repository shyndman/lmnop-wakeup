from datetime import datetime
from enum import StrEnum, auto

from loguru import logger
from pydantic import BaseModel

from ..core.date import end_of_local_day, start_of_local_day
from ..env import ApiKey, get_hass_api_key
from .calendar import gcalendar_api, hass_calendar_api
from .model import Calendar


class CalendarEventFilter(StrEnum):
  no_filter = auto()
  today_only = auto()


class CalendarInfo(BaseModel):
  notes: str
  event_filter: CalendarEventFilter = CalendarEventFilter.no_filter


# Define a constant dictionary mapping calendar entity IDs to instruction strings.
CALENDAR_INSTRUCTIONS = {
  # Scott's personal calendar
  "scotty.hyndman@gmail.com": CalendarInfo(
    notes="This is Scott's personal calendar. These are high priority events "
    "for wakeups and reminders, unless the event states otherwise."
  ),
  # Scott's birthday calendar
  "md3ntu1lbq9vqc59fs75svbusg@group.calendar.google.com": CalendarInfo(
    notes="This is a birthday calendar. Short reminders for these can start a couple weeks before "
    "the event, but they are not high priority unless they are for immediate family."
  ),
  # Doncaster calendar
  "family16125668672800183011@group.calendar.google.com": CalendarInfo(
    notes="This is a family calendar. These are high priority events for wakeups and reminders. "
    "The creator of the event and its attendees should indicate whether it applies to Hilary or "
    "Scott, or both. If attendees do not indicate both are attending, but the description or "
    "summary does, assume both are attending. "
  ),
  # Hilary's work calendar
  "calendar.hilary_s_work": CalendarInfo(
    notes="This is Hilary's work calendar. While the events are private, they are all high "
    "priority, and should result in wakeups and reminders. Refer to the events as meetings, not "
    '"busy" event.',
    event_filter=CalendarEventFilter.today_only,
  ),
  # Ontario statuatory holidays
  "calendar.ontario_holidays": CalendarInfo(
    notes="These are Ontario statuatory holidays, and indicate that Hilary's work calendar can "
    "be ignored, and we can use our later wakeup time."
  ),
  # Radarr
  "calendar.radarr": CalendarInfo(
    notes="Upcoming movies. Low priority, but because Hilary and Scott like movies so much, it "
    "might be good to surface something coming up. Also worth mentioning, are dense groupings of "
    "upcoming movies."
  ),
  # Sonarr
  "calendar.sonarr": CalendarInfo(
    notes="Television shows coming to our media center. Low priority, but when we get into a show"
    "we love hearing about every upcoming episode."
  ),
  # Waste collection schedule
  "calendar.toronto_on": CalendarInfo(
    notes="This is Toronto's waste collection schedule. It is important that we're told the day "
    "before so we can have the bins out when the trucks come around, in the early morning. These "
    "are high-ish priority. We should at least get a sentence reminder. "
    "Legend: GreenBin=Organics YardWaste=Leaves, yard clippings, etc. BlueBin=Recycling",
  ),
}


async def get_filtered_calendars_with_notes(
  briefing_date: datetime,
  start_ts: datetime,
  end_ts: datetime,
  hass_api_token: ApiKey | None = None,
) -> list[Calendar]:
  """
  Fetches calendars from Google Calendar and Home Assistant, filters them based on
  CALENDAR_INSTRUCTIONS, and assigns notes for processing.
  """
  logger.info(
    "Fetching Google Calendars between {start_ts} and {end_ts}", start_ts=start_ts, end_ts=end_ts
  )
  google_calendars = gcalendar_api.calendar_events_in_range(start_ts, end_ts)
  logger.info("Fetched {num_google_cals} Google Calendars", num_google_cals=len(google_calendars))

  logger.info(
    "Fetching Home Assistant Calendars between {start_ts} and {end_ts}",
    start_ts=start_ts,
    end_ts=end_ts,
  )
  hass_calendars = await hass_calendar_api.calendar_events_in_range(
    start_ts, end_ts, hass_api_token or get_hass_api_key()
  )
  logger.info("Fetched {num_hass_cals} Home Assistant Calendars", num_hass_cals=len(hass_calendars))

  all_calendars = google_calendars + hass_calendars
  logger.info(
    "Combined calendars from both sources. Total: {total_cals}", total_cals=len(all_calendars)
  )

  filtered_calendars: list[Calendar] = []
  for calendar in all_calendars:
    if calendar.entity_id not in CALENDAR_INSTRUCTIONS:
      logger.info(
        "Skipping calendar {calendar_id} as it is not in the instructions",
        calendar_id=calendar.entity_id,
      )
      continue

    instructions = CALENDAR_INSTRUCTIONS[calendar.entity_id]
    calendar.notes_for_processing = instructions.notes
    if instructions.event_filter == CalendarEventFilter.today_only:
      # Filter to only include today's events

      calendar.events = calendar.filter_events_by_range(
        start_of_local_day(briefing_date),
        end_of_local_day(briefing_date),
      )

    filtered_calendars.append(calendar)

  logger.info(
    "Filtered calendars based on instructions. Included: {num_filtered_cals}",
    num_filtered_cals=len(filtered_calendars),
  )
  return filtered_calendars
