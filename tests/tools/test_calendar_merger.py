import asyncio
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from lmnop_wakeup.common import ApiKey, Calendar, CalendarEvent, TimeInfo
from lmnop_wakeup.tools.calendar_merger import (
    enrich_and_filter_calendars,
    get_merged_calendars,
)

# Helper function to create dummy TimeInfo
def create_time_info_date(year: int, month: int, day: int) -> TimeInfo:
    return TimeInfo(date=date(year, month, day))

def create_time_info_datetime(year: int, month: int, day: int, hour: int, minute: int) -> TimeInfo:
    return TimeInfo(dateTime=datetime(year, month, day, hour, minute))

# Helper function to create dummy CalendarEvent
def create_event(summary: str, start_year: int, start_month: int, start_day: int) -> CalendarEvent:
    return CalendarEvent(summary=summary, start_ts=create_time_info_date(start_year, start_month, start_day))

# Helper function to create dummy Calendar
def create_calendar(entity_id: str, name: str, events: list[CalendarEvent] | None = None) -> Calendar:
    return Calendar(entity_id=entity_id, name=name, events=events or [])

@pytest.mark.asyncio
async def test_get_merged_calendars_successful_merge():
    """
    Test Case 1.1: Successful merge of calendars from both sources.
    """
    start_ts = datetime(2023, 1, 1, 0, 0, 0)
    end_ts = datetime(2023, 1, 2, 0, 0, 0)
    dummy_token = ApiKey("dummy_token")

    gcal_event1 = create_event("GCal Event 1", 2023, 1, 1)
    gcal_cal1 = create_calendar("gcal_id1", "Google Calendar 1", [gcal_event1])
    mock_gcal_calendars = [gcal_cal1]

    hass_event1 = create_event("HASS Event 1", 2023, 1, 1)
    hass_cal1 = create_calendar("hass_id1", "HASS Calendar 1", [hass_event1])
    mock_hass_calendars = [hass_cal1]

    with patch("lmnop_wakeup.tools.gcalendar_api.calendar_events_in_range", MagicMock(return_value=mock_gcal_calendars)) as mock_gcal_func, \
         patch("lmnop_wakeup.tools.hass_api.calendar_events_in_range", MagicMock(return_value=asyncio.Future())) as mock_hass_func:
        
        mock_hass_func.return_value.set_result(mock_hass_calendars) # Set future result for async mock

        result = await get_merged_calendars(start_ts, end_ts, dummy_token)

        mock_gcal_func.assert_called_once_with(start_ts, end_ts)
        mock_hass_func.assert_called_once_with(start_ts, end_ts, dummy_token)
        
        assert len(result) == 2
        assert gcal_cal1 in result
        assert hass_cal1 in result

@pytest.mark.asyncio
async def test_get_merged_calendars_one_source_empty():
    """
    Test Case 1.2: One source returns calendars, the other returns empty.
    """
    start_ts = datetime(2023, 1, 1, 0, 0, 0)
    end_ts = datetime(2023, 1, 2, 0, 0, 0)
    dummy_token = ApiKey("dummy_token")

    hass_event1 = create_event("HASS Event 1", 2023, 1, 1)
    hass_cal1 = create_calendar("hass_id1", "HASS Calendar 1", [hass_event1])
    mock_hass_calendars = [hass_cal1]

    # Scenario 1: gCalendar empty, HASS has data
    with patch("lmnop_wakeup.tools.gcalendar_api.calendar_events_in_range", MagicMock(return_value=[])) as mock_gcal_func_empty, \
         patch("lmnop_wakeup.tools.hass_api.calendar_events_in_range", MagicMock(return_value=asyncio.Future())) as mock_hass_func_data:
        
        mock_hass_func_data.return_value.set_result(mock_hass_calendars)

        result = await get_merged_calendars(start_ts, end_ts, dummy_token)
        
        mock_gcal_func_empty.assert_called_once_with(start_ts, end_ts)
        mock_hass_func_data.assert_called_once_with(start_ts, end_ts, dummy_token)
        assert len(result) == 1
        assert hass_cal1 in result

    # Scenario 2: gCalendar has data, HASS empty
    gcal_event1 = create_event("GCal Event 1", 2023, 1, 1)
    gcal_cal1 = create_calendar("gcal_id1", "Google Calendar 1", [gcal_event1])
    mock_gcal_calendars = [gcal_cal1]

    with patch("lmnop_wakeup.tools.gcalendar_api.calendar_events_in_range", MagicMock(return_value=mock_gcal_calendars)) as mock_gcal_func_data, \
         patch("lmnop_wakeup.tools.hass_api.calendar_events_in_range", MagicMock(return_value=asyncio.Future())) as mock_hass_func_empty:

        mock_hass_func_empty.return_value.set_result([])
        
        result = await get_merged_calendars(start_ts, end_ts, dummy_token)

        mock_gcal_func_data.assert_called_once_with(start_ts, end_ts)
        mock_hass_func_empty.assert_called_once_with(start_ts, end_ts, dummy_token)
        assert len(result) == 1
        assert gcal_cal1 in result

@pytest.mark.asyncio
async def test_get_merged_calendars_both_sources_empty():
    """
    Test Case 1.3: Both sources return empty lists.
    """
    start_ts = datetime(2023, 1, 1, 0, 0, 0)
    end_ts = datetime(2023, 1, 2, 0, 0, 0)
    dummy_token = ApiKey("dummy_token")

    with patch("lmnop_wakeup.tools.gcalendar_api.calendar_events_in_range", MagicMock(return_value=[])) as mock_gcal_func, \
         patch("lmnop_wakeup.tools.hass_api.calendar_events_in_range", MagicMock(return_value=asyncio.Future())) as mock_hass_func:
        
        mock_hass_func.return_value.set_result([])

        result = await get_merged_calendars(start_ts, end_ts, dummy_token)
        
        mock_gcal_func.assert_called_once_with(start_ts, end_ts)
        mock_hass_func.assert_called_once_with(start_ts, end_ts, dummy_token)
        assert len(result) == 0


def test_enrich_and_filter_calendars_enrich_and_keep():
    """
    Test Case 2.1: Enrich a calendar and keep it.
    """
    cal1_event = create_event("Event Cal1", 2023, 1, 1)
    cal1 = create_calendar("id1", "Calendar 1", [cal1_event])
    cal2_event = create_event("Event Cal2", 2023, 1, 2)
    cal2 = create_calendar("id2", "Calendar 2", [cal2_event])
    
    descriptions_map = {"id1": "Description for cal1"}
    
    result = enrich_and_filter_calendars([cal1, cal2], descriptions_map)
    
    assert len(result) == 1
    assert result[0].entity_id == "id1"
    assert result[0].notes_for_processing == "Description for cal1"
    # Ensure original object is modified if that's the design, or a copy is returned
    assert cal1.notes_for_processing == "Description for cal1" 

def test_enrich_and_filter_calendars_filter_out():
    """
    Test Case 2.2: Filter out calendars not in the descriptions_map.
    """
    cal1 = create_calendar("id1", "Calendar 1")
    cal2 = create_calendar("id2", "Calendar 2")
    
    descriptions_map = {"id_unknown": "Some description"}
    
    result = enrich_and_filter_calendars([cal1, cal2], descriptions_map)
    
    assert len(result) == 0

def test_enrich_and_filter_calendars_mixed_enrich_and_filter():
    """
    Test Case 2.3: Mixed enrichment and filtering.
    """
    cal1 = create_calendar("id1", "Calendar 1")
    cal2 = create_calendar("id2", "Calendar 2") # This one will be filtered out
    cal3_event = create_event("Event Cal3", 2023, 1, 3)
    cal3 = create_calendar("id3", "Calendar 3", [cal3_event])
    
    descriptions_map = {
        "id1": "Desc1",
        "id3": "Desc3"
    }
    
    input_calendars = [cal1, cal2, cal3]
    result = enrich_and_filter_calendars(input_calendars, descriptions_map)
    
    assert len(result) == 2
    result_ids = {cal.entity_id for cal in result}
    assert "id1" in result_ids
    assert "id3" in result_ids
    
    for cal in result:
        if cal.entity_id == "id1":
            assert cal.notes_for_processing == "Desc1"
            assert cal1.notes_for_processing == "Desc1" # Check original object
        elif cal.entity_id == "id3":
            assert cal.notes_for_processing == "Desc3"
            assert cal3.notes_for_processing == "Desc3" # Check original object

def test_enrich_and_filter_calendars_empty_input_calendars():
    """
    Test Case 2.4: Empty list of input calendars.
    """
    descriptions_map = {"id1": "Desc1"}
    result = enrich_and_filter_calendars([], descriptions_map)
    assert len(result) == 0

def test_enrich_and_filter_calendars_empty_descriptions_map():
    """
    Test Case 2.5: Empty descriptions map.
    """
    cal1 = create_calendar("id1", "Calendar 1")
    result = enrich_and_filter_calendars([cal1], {})
    assert len(result) == 0

# Example of creating TimeInfo with dateTime for completeness in helpers
# This isn't strictly needed by current tests but good for future use
def _test_helper_timeinfo_datetime():
    ti = create_time_info_datetime(2023, 1, 1, 10, 0)
    assert ti.dateTime == datetime(2023,1,1,10,0)
    assert ti.date is None

def _test_helper_timeinfo_date():
    ti = create_time_info_date(2023,1,1)
    assert ti.date == date(2023,1,1)
    assert ti.dateTime is None

def _test_helper_create_event_with_datetime():
    event = CalendarEvent(summary="Timed Event", start_ts=create_time_info_datetime(2023,1,1,10,0))
    assert event.summary == "Timed Event"
    assert event.start_ts.dateTime is not None
