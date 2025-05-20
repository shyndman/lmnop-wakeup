import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from lmnop_wakeup.common import ApiKey, Calendar, CalendarEvent, TimeInfo
from lmnop_wakeup.schedule.timekeeper import calendar_events_for_scheduling

@pytest.mark.asyncio
@patch('lmnop_wakeup.schedule.timekeeper.CALENDAR_DESCRIPTIONS_MAP', new={'cal_id_1': 'Test Desc From Mock Map'})
@patch('lmnop_wakeup.schedule.timekeeper.get_hass_api_key')
@patch('lmnop_wakeup.schedule.timekeeper.enrich_and_filter_calendars')
@patch('lmnop_wakeup.schedule.timekeeper.get_merged_calendars')
async def test_calendar_events_for_scheduling_flow(
    mock_get_merged_calendars: MagicMock,
    mock_enrich_and_filter_calendars: MagicMock,
    mock_get_hass_api_key: MagicMock,
):
    # Arrange
    mock_get_hass_api_key.return_value = ApiKey('fake_token')
    
    sample_merged_cal_1 = Calendar(entity_id='cal_id_1', name='Merged Cal 1')
    sample_merged_cal_2 = Calendar(entity_id='cal_id_2', name='Merged Cal 2')
    # Ensure the mock for an async function is awaitable if the function it replaces is.
    # get_merged_calendars is async, so its mock should be configured to be awaitable.
    # However, its return_value is a list, not a coroutine, so just setting return_value is fine.
    mock_get_merged_calendars.return_value = [sample_merged_cal_1, sample_merged_cal_2]
    
    expected_final_cal = Calendar(entity_id='cal_id_1', name='Merged Cal 1', notes_for_processing='Test Desc From Mock Map')
    mock_enrich_and_filter_calendars.return_value = [expected_final_cal]

    start_ts = datetime(2024, 1, 1, 0, 0, 0)
    end_ts = datetime(2024, 1, 1, 23, 59, 59)

    # Act
    result_calendars = await calendar_events_for_scheduling(start_ts, end_ts)

    # Assert
    mock_get_hass_api_key.assert_called_once()
    mock_get_merged_calendars.assert_called_once_with(
        start_ts=start_ts, end_ts=end_ts, hass_api_token=ApiKey('fake_token')
    )
    mock_enrich_and_filter_calendars.assert_called_once_with(
        calendars=[sample_merged_cal_1, sample_merged_cal_2],
        descriptions_map={'cal_id_1': 'Test Desc From Mock Map'}
    )
    assert result_calendars == [expected_final_cal]
