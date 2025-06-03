import re
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum, auto

from langgraph.func import task
from loguru import logger
from pydantic import BaseModel

from ..core.date import end_of_local_day, start_of_local_day
from ..env import ApiKey, get_hass_api_key
from .calendar import gcalendar_api, hass_calendar_api
from .model import Calendar, CalendarEvent


class CalendarEventFilter(StrEnum):
  no_filter = auto()
  today_only = auto()


class CalendarInfo(BaseModel):
  notes: str
  event_filter: CalendarEventFilter = CalendarEventFilter.no_filter
  event_mapper: Callable[[CalendarEvent], CalendarEvent] | None = None


series_pattern_1 = re.compile(r"[sS]0*(\d+)[eE]0*(\d+)")
series_pattern_2 = re.compile(r"0*(\d+)x0*(\d+)")


def expand_sonarr_series(e: CalendarEvent) -> CalendarEvent:
  e.summary = series_pattern_1.sub(r"Season \1 Episode \2", e.summary)
  e.summary = series_pattern_2.sub(r"Season \1 Episode \2", e.summary)
  return e


# Define a constant dictionary mapping calendar entity IDs to instruction strings.
CALENDAR_INSTRUCTIONS = {
  # Scott's personal calendar
  "scotty.hyndman@gmail.com": CalendarInfo(
    notes="This is Scott's personal calendar. These are priority events "
    "for wakeups and reminders, unless the event states otherwise."
  ),
  # Scott's birthday calendar
  "md3ntu1lbq9vqc59fs75svbusg@group.calendar.google.com": CalendarInfo(
    notes="This is Scott's birthday calendar. Short reminders for these can start a couple weeks "
    "before the event, but they are not elevated priority unless they are for immediate family."
  ),
  # Doncaster calendar
  "family16125668672800183011@group.calendar.google.com": CalendarInfo(
    notes="This is Scott and Hilary's shared calendar. These are priority events for "
    "wakeups and reminders. The creator of the event and its attendees should indicate whether it "
    "applies to Hilary or Scott, or both. If attendees do not indicate both are attending, but "
    "the description or summary does, assume both are attending. "
  ),
  # Hilary's work calendar
  "calendar.hilary_s_work": CalendarInfo(
    notes="This is Hilary's work calendar. While the events are private, they are higher "
    "priority IN THE MORNING and should result in wakeups and reminders. Refer to the events as "
    'meetings, not "busy" event, and NEVER mention them as being high priority.',
    event_filter=CalendarEventFilter.today_only,
  ),
  # Ontario statuatory holidays
  "calendar.ontario_holidays": CalendarInfo(
    notes="These are Ontario statuatory holidays, and indicate that Hilary's work calendar can "
    "be ignored, and we can use our later wakeup time. They're also important to remind people "
    "about."
  ),
  # Radarr
  "calendar.radarr": CalendarInfo(
    notes="Upcoming movies. Standard priority. These are movies coming to Scott and Hilary's "
    "streaming services. But just because a movie is on this calendar doesn't mean they "
    "will be interested in hearing about it, so if corroborating evidence is availble (whether "
    "that's signals of Scott and Hilary's preferences, or a movie's high review scores), use "
    "those when determining whether or not to surface an upcoming feature. Events from this "
    "calendar should never appear in any lists of a previous day's notable events."
  ),
  # Sonarr
  "calendar.sonarr": CalendarInfo(
    notes="Upcoming television show episodes. Television shows coming to our media center. "
    "Standard priority, but when we get into a show we love hearing about every upcoming "
    "episode. Events from this calendar should never appear in any lists of a previous day's "
    "notable events.",
    event_mapper=expand_sonarr_series,
  ),
  # Waste collection schedule
  "calendar.toronto_on": CalendarInfo(
    notes="This is Toronto's waste collection schedule. It is important that we're told the day "
    "before so we can have the bins out when the trucks come around, in the early morning. These "
    "are high-ish priority. We should at least get a sentence reminder. "
    "Language-wise, GreenBin also goes by organics, YardWaste=leaves and twig collection, "
    "yard clippings, etc. BlueBin=Recycling, cardboard",
  ),
}


@task()
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
    if instructions.event_mapper is not None:
      calendar.events = list(map(instructions.event_mapper, calendar.events))

    filtered_calendars.append(calendar)

  logger.info(
    "Filtered calendars based on instructions. Included: {num_filtered_cals}",
    num_filtered_cals=len(filtered_calendars),
  )
  return filtered_calendars
