from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import AwareDatetime

from lmnop_wakeup.core.date import TimeInfo
from lmnop_wakeup.events.model import (
  Calendar,
  CalendarEmailUser,
  CalendarEvent,
  CalendarsOfInterest,
  CalendarUser,
)


# Helper for creating timezone-aware datetimes
def create_aware_datetime(
  year: int,
  month: int,
  day: int,
  hour: int = 0,
  minute: int = 0,
  second: int = 0,
  microsecond: int = 0,
  tz_str: str = "America/Toronto",
) -> AwareDatetime:
  dt = datetime(year, month, day, hour, minute, second, microsecond)
  return dt.replace(tzinfo=ZoneInfo(tz_str))


# Test CalendarEmailUser
def test_calendar_email_user():
  user = CalendarEmailUser(email="test@example.com")
  assert user.email == "test@example.com"


# Test CalendarUser
def test_calendar_user():
  user = CalendarUser(email="test@example.com", displayName="Test User")
  assert user.email == "test@example.com"
  assert user.display_name == "Test User"


# Test CalendarEvent
def test_calendar_event_regular():
  start_dt = create_aware_datetime(2025, 5, 24, 9, 0)
  end_dt = create_aware_datetime(2025, 5, 24, 10, 0)
  event = CalendarEvent(
    summary="Meeting",
    start=TimeInfo(dateTime=start_dt),
    end=TimeInfo(dateTime=end_dt),
  )
  assert event.summary == "Meeting"
  assert not event.is_all_day()
  assert event.start_datetime_aware == start_dt
  assert event.end_datetime_aware == end_dt


def test_calendar_event_all_day():
  start_date = date(2025, 5, 24)
  event = CalendarEvent(
    summary="Holiday",
    start=TimeInfo(date=start_date, timeZone="America/Toronto"),
    end=None,
  )
  assert event.summary == "Holiday"
  assert event.is_all_day()

  # For all-day events, start_datetime_aware should be start of the day
  expected_start = create_aware_datetime(2025, 5, 24, 0, 0, 0, 0, "America/Toronto")
  assert event.start_datetime_aware == expected_start

  # For all-day events, end_datetime_aware should be end of the day
  expected_end = create_aware_datetime(2025, 5, 24, 23, 59, 59, 999999, "America/Toronto")
  assert event.end_datetime_aware == expected_end


# Test overlaps_with_range
@pytest.mark.parametrize(
  "event_start_h, event_end_h, range_start_h, range_end_h, expected_overlap",
  [
    # Full overlap
    (9, 10, 8, 11, True),
    # Partial overlap (event starts before, ends within)
    (8, 10, 9, 11, True),
    # Partial overlap (event starts within, ends after)
    (9, 11, 8, 10, True),
    # Event fully within range
    (9, 10, 8, 11, True),
    # No overlap (event before range)
    (7, 8, 9, 10, False),
    # No overlap (event after range)
    (11, 12, 9, 10, False),
    # Edge case: event ends exactly at range start
    (8, 9, 9, 10, False),
    # Edge case: event starts exactly at range end
    (10, 11, 9, 10, False),
    # Edge case: event starts at range end, but has duration
    (10, 10.5, 9, 10, False),
    # Edge case: event ends at range start, but has duration
    (8.5, 9, 9, 10, False),
  ],
)
def test_overlaps_with_range_regular_events(
  event_start_h, event_end_h, range_start_h, range_end_h, expected_overlap
):
  event_start = create_aware_datetime(
    2025, 5, 24, int(event_start_h), int((event_start_h % 1) * 60)
  )
  event_end = create_aware_datetime(2025, 5, 24, int(event_end_h), int((event_end_h % 1) * 60))
  range_start = create_aware_datetime(
    2025, 5, 24, int(range_start_h), int((range_start_h % 1) * 60)
  )
  range_end = create_aware_datetime(2025, 5, 24, int(range_end_h), int((range_end_h % 1) * 60))

  event = CalendarEvent(
    summary="Test Event",
    start=TimeInfo(dateTime=event_start),
    end=TimeInfo(dateTime=event_end),
  )
  assert event.overlaps_with_range(range_start, range_end) == expected_overlap


@pytest.mark.parametrize(
  "event_day, range_start_day, range_end_day, expected_overlap",
  [
    # All-day event fully within range
    (24, 23, 25, True),
    # All-day event partially overlaps (starts before, ends within)
    (23, 23, 24, True),
    # All-day event partially overlaps (starts within, ends after)
    (24, 23, 24, True),
    # All-day event no overlap (before range)
    (22, 23, 24, False),
    # All-day event no overlap (after range)
    (25, 23, 24, False),
    # All-day event exactly at range start (start of day)
    (
      23,
      23,
      24,
      True,
    ),  # Event day 23, range 23-24. Event ends 23:59:59.999999 on day 23. Range starts 00:00:00 on
    # day 23.
    # All-day event exactly at range end (end of day)
    (
      24,
      23,
      24,
      True,
    ),  # Event day 24, range 23-24. Event starts 00:00:00 on day 24. Range ends 00:00:00 on day 24.
  ],
)
def test_overlaps_with_range_all_day_events(
  event_day, range_start_day, range_end_day, expected_overlap
):
  event_date = date(2025, 5, event_day)
  event = CalendarEvent(
    summary="All Day Event", start=TimeInfo(date=event_date, timeZone="America/Toronto"), end=None
  )

  range_start = create_aware_datetime(2025, 5, range_start_day, 0, 0, 0, 0, "America/Toronto")
  range_end = create_aware_datetime(2025, 5, range_end_day, 23, 59, 59, 999999, "America/Toronto")

  assert event.overlaps_with_range(range_start, range_end) == expected_overlap


# Test Calendar
def test_calendar_filter_events_by_range():
  cal = Calendar(entity_id="test_cal", name="Test Calendar")
  start_range = create_aware_datetime(2025, 5, 24, 9, 0)
  end_range = create_aware_datetime(2025, 5, 24, 11, 0)

  # Event within range
  event1 = CalendarEvent(
    summary="Event 1",
    start=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 9, 30)),
    end=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 10, 30)),
  )
  # Event outside range
  event2 = CalendarEvent(
    summary="Event 2",
    start=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 7, 0)),
    end=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 8, 0)),
  )
  # All-day event overlapping
  event3 = CalendarEvent(
    summary="All Day Event",
    start=TimeInfo(date=date(2025, 5, 24), timeZone="America/Toronto"),
    end=None,
  )
  # All-day event not overlapping
  event4 = CalendarEvent(
    summary="Another All Day Event",
    start=TimeInfo(date=date(2025, 5, 25), timeZone="America/Toronto"),
    end=None,
  )

  cal.events.extend([event1, event2, event3, event4])

  filtered = cal.filter_events_by_range(start_range, end_range)
  assert len(filtered) == 2
  assert event1 in filtered
  assert event3 in filtered
  assert event2 not in filtered
  assert event4 not in filtered


# Test CalendarSet
def test_calendar_set_filter():
  cal1 = Calendar(entity_id="cal1", name="Work")
  cal2 = Calendar(entity_id="cal2", name="Personal")
  cal3 = Calendar(entity_id="cal3", name="Family")

  start_range = create_aware_datetime(2025, 5, 24, 9, 0)
  end_range = create_aware_datetime(2025, 5, 24, 11, 0)

  # Event for cal1 (overlaps)
  cal1.events.append(
    CalendarEvent(
      summary="Work Meeting",
      start=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 9, 30)),
      end=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 10, 30)),
    )
  )
  # Event for cal2 (no overlap)
  cal2.events.append(
    CalendarEvent(
      summary="Personal Appointment",
      start=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 12, 0)),
      end=TimeInfo(dateTime=create_aware_datetime(2025, 5, 24, 13, 0)),
    )
  )
  # Event for cal3 (overlaps)
  cal3.events.append(
    CalendarEvent(
      summary="Family Dinner",
      start=TimeInfo(date=date(2025, 5, 24), timeZone="America/Toronto"),
      end=None,
    )
  )

  cal_set = CalendarsOfInterest(calendars_by_id={"cal1": cal1, "cal2": cal2, "cal3": cal3})

  # Test filter without name_inclusion_list
  filtered_set = cal_set.filter(start_range, end_range)
  assert len(filtered_set.calendars_by_id) == 2
  assert "cal1" in filtered_set.calendars_by_id
  assert "cal3" in filtered_set.calendars_by_id
  assert "cal2" not in filtered_set.calendars_by_id
  assert len(filtered_set.calendars_by_id["cal1"].events) == 1
  assert len(filtered_set.calendars_by_id["cal3"].events) == 1

  # Test filter with name_inclusion_list
  filtered_set_with_names = cal_set.filter(start_range, end_range, name_inclusion_list={"Work"})
  assert len(filtered_set_with_names.calendars_by_id) == 1
  assert "cal1" in filtered_set_with_names.calendars_by_id
  assert "cal3" not in filtered_set_with_names.calendars_by_id
  assert len(filtered_set_with_names.calendars_by_id["cal1"].events) == 1

  # Test filter with name_inclusion_list where no calendars match
  filtered_set_no_match = cal_set.filter(
    start_range, end_range, name_inclusion_list={"NonExistent"}
  )
  assert len(filtered_set_no_match.calendars_by_id) == 0

  # Test filter where no events overlap
  no_overlap_start = create_aware_datetime(2025, 5, 25, 0, 0)
  no_overlap_end = create_aware_datetime(2025, 5, 25, 1, 0)
  filtered_set_no_events = cal_set.filter(no_overlap_start, no_overlap_end)
  assert len(filtered_set_no_events.calendars_by_id) == 0
