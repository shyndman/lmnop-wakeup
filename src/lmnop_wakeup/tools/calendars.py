from datetime import datetime

from loguru import logger

from lmnop_wakeup.common import ApiKey, Calendar

from . import gcalendar_api, hass_api

# Define a constant dictionary mapping calendar entity IDs to instruction strings.
# TODO: Replace placeholder IDs and instructions with actual values.
CALENDAR_INSTRUCTIONS = {
  # Scott's personal calendar
  "scotty.hyndman@gmail.com": "This is Scott's personal calendar. These are high priority events "
  "for wakeups and reminders, unless the event states otherwise.",
  # Scott's birthday calendar
  "md3ntu1lbq9vqc59fs75svbusg@group.calendar.google.com": "This is a birthday calendar. Short "
  "reminders for these can start a couple weeks before the event, but they are not high priority "
  "unless they are for immediate family.",
  # Doncaster calendar
  "family16125668672800183011@group.calendar.google.com": "This is a family calendar. These are "
  "high priority events for wakeups and reminders. The creator of the event should be available "
  "and will be either Hilary or Scott.",
  # Hilary's work calendar
  "calendar.hilary_s_work": "This is Hilary's work calendar. While the events are private, they "
  "are all high priority, and should result in wakeups and reminders.",
  # Ontario statuatory holidays
  "calendar.ontario_holidays": "These are Ontario statuatory holidays, and indicate that Hilary's"
  "work calendar can be ignored, and we can use our later wakeup time.",
  # Radarr
  "calendar.radarr": "Upcoming movies. Low priority, but might be worth a mention, especially "
  "if there's a dense grouping ahead.",
  # Sonarr
  "calendar.sonarr": "Television shows coming to our media center. Low priority, but might be "
  "worth a mention, especially if there's a dense grouping ahead.",
  # Waste collection schedule
  "calendar.toronto_on": "This is Toronto's waste collection schedule. It is important that "
  "we're told the day before so we can have the bins out when the trucks come around, in the "
  "early morning.",
}


async def get_filtered_calendars_with_notes(
  start_ts: datetime,
  end_ts: datetime,
  hass_api_token: ApiKey,
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
  hass_calendars = await hass_api.calendar_events_in_range(start_ts, end_ts, hass_api_token)
  logger.info("Fetched {num_hass_cals} Home Assistant Calendars", num_hass_cals=len(hass_calendars))

  all_calendars = google_calendars + hass_calendars
  logger.info(
    "Combined calendars from both sources. Total: {total_cals}", total_cals=len(all_calendars)
  )

  filtered_calendars: list[Calendar] = []
  for calendar in all_calendars:
    if calendar.entity_id in CALENDAR_INSTRUCTIONS:
      calendar.notes_for_processing = CALENDAR_INSTRUCTIONS[calendar.entity_id]
      filtered_calendars.append(calendar)
    else:
      logger.info(
        "Skipping calendar {calendar_id} as it is not in the instructions",
        calendar_id=calendar.entity_id,
      )

  logger.info(
    "Filtered calendars based on instructions. Included: {num_filtered_cals}",
    num_filtered_cals=len(filtered_calendars),
  )
  return filtered_calendars
