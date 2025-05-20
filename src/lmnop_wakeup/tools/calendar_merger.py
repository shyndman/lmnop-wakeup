from datetime import datetime

from lmnop_wakeup.common import ApiKey, Calendar
from lmnop_wakeup.tools import gcalendar_api, hass_api


async def get_merged_calendars(
    start_ts: datetime,
    end_ts: datetime,
    hass_api_token: ApiKey,
) -> list[Calendar]:
    """
    Fetches calendar events from Google Calendar and HASS and merges them.

    Args:
        start_ts: The start timestamp for fetching events.
        end_ts: The end timestamp for fetching events.
        hass_api_token: The API key for HASS.

    Returns:
        A list of Calendar objects containing events from both sources.
    """
    gcal_calendars = gcalendar_api.calendar_events_in_range(start_ts, end_ts)
    hass_calendars = await hass_api.calendar_events_in_range(start_ts, end_ts, hass_api_token)

    merged_calendars = gcal_calendars + hass_calendars
    return merged_calendars


def enrich_and_filter_calendars(
    calendars: list[Calendar],
    descriptions_map: dict[str, str]  # Key: calendar entity_id, Value: description string
) -> list[Calendar]:
    """
    Filters a list of Calendar objects based on a descriptions map and
    enriches the matching calendars with notes for processing.

    Args:
        calendars: A list of Calendar objects to filter and enrich.
        descriptions_map: A dictionary where keys are calendar entity_ids
                          and values are description strings to be added as notes.

    Returns:
        A new list of Calendar objects that were found in the descriptions_map,
        with their notes_for_processing attribute set.
    """
    enriched_and_filtered_calendars: list[Calendar] = []
    for calendar in calendars:
        if calendar.entity_id in descriptions_map:
            calendar.notes_for_processing = descriptions_map[calendar.entity_id]
            enriched_and_filtered_calendars.append(calendar)
    return enriched_and_filtered_calendars
