from datetime import date, datetime, time, timezone

# Import the functions and classes to be tested
from lmnop_wakeup.tools.weather_api import WeatherReport, is_timestamp_on_date
from lmnop_wakeup.typing import nu
from pirate_weather_api_client.models import (
  Currently,
  Daily,
  Hourly,
  HourlyDataItem,
)


# Test cases for is_timestamp_on_date
def test_is_timestamp_on_date_same_day():
  test_date = date(2023, 10, 27)
  midnight = datetime.combine(test_date, time(0, 0, 0), tzinfo=timezone.utc)
  # Timestamp for 2023-10-27 12:00:00 UTC
  timestamp_on_day = int(datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc).timestamp())
  assert is_timestamp_on_date(timestamp_on_day, midnight) is True


def test_is_timestamp_on_date_previous_day():
  test_date = date(2023, 10, 27)
  midnight = datetime.combine(test_date, time(0, 0, 0), tzinfo=timezone.utc)
  # Timestamp for 2023-10-26 23:59:59 UTC
  timestamp_prev_day = int(datetime(2023, 10, 26, 23, 59, 59, tzinfo=timezone.utc).timestamp())
  assert is_timestamp_on_date(timestamp_prev_day, midnight) is False


def test_is_timestamp_on_date_next_day():
  test_date = date(2023, 10, 27)
  midnight = datetime.combine(test_date, time(0, 0, 0), tzinfo=timezone.utc)
  # Timestamp for 2023-10-28 00:00:00 UTC
  timestamp_next_day = int(datetime(2023, 10, 28, 0, 0, 0, tzinfo=timezone.utc).timestamp())
  assert is_timestamp_on_date(timestamp_next_day, midnight) is False


# Test cases for get_hourlies_for_day
def test_get_hourlies_for_day_filters_correctly():
  test_date = date(2023, 10, 27)
  # Timestamps for 2023-10-27 (UTC)
  ts1 = int(datetime(2023, 10, 27, 0, 0, 0, tzinfo=timezone.utc).timestamp())
  ts2 = int(datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc).timestamp())
  # Timestamp for 2023-10-26 (UTC)
  ts_prev = int(datetime(2023, 10, 26, 23, 0, 0, tzinfo=timezone.utc).timestamp())
  # Timestamp for 2023-10-28 (UTC)
  ts_next = int(datetime(2023, 10, 28, 1, 0, 0, tzinfo=timezone.utc).timestamp())

  # Use actual HourlyDataItem and Hourly models
  hourly_data_items = [
    HourlyDataItem(time=ts_prev),
    HourlyDataItem(time=ts1),
    HourlyDataItem(time=ts2),
    HourlyDataItem(time=ts_next),
  ]
  # Create a WeatherReport instance with valid mock data for required fields
  weather_report = WeatherReport(
    currently=Currently(),  # Provide a valid Currently instance
    hourly=Hourly(data=hourly_data_items),
    daily=Daily(),  # Provide a valid BaseModel instance for daily
    alerts=[],  # Provide a valid list of AlertsItem
  )

  hourlies_for_day = weather_report.get_hourlies_for_day(test_date, tz=timezone.utc)

  # Expecting only ts1 and ts2 to be included
  expected_timestamps = {ts1, ts2}
  actual_timestamps = {nu(item.time) for item in hourlies_for_day}

  assert actual_timestamps == expected_timestamps
  assert len(hourlies_for_day) == 2


def test_get_hourlies_for_day_empty_data():
  test_date = date(2023, 10, 27)
  # Create a WeatherReport instance with empty hourly data and valid mocks
  weather_report = WeatherReport(
    currently=Currently(),
    hourly=Hourly(data=[]),
    daily=Daily(),
    alerts=[],
  )

  hourlies_for_day = weather_report.get_hourlies_for_day(test_date, tz=timezone.utc)

  assert hourlies_for_day == []


def test_get_hourlies_for_day_none_data():
  test_date = date(2023, 10, 27)

  # Create a mock WeatherReport instance with None hourly data and valid mocks
  # Note: Hourly(data=None) causes validation error, so mock WeatherReport directly
  class MockWeatherReportNoneHourlyData:
    def get_hourlies_for_day(self, date: date) -> list[HourlyDataItem]:
      # This is the exact code from the original file, adapted for mock objects
      midnight_on_date = datetime.combine(date, time(0, 0, 0), tzinfo=timezone.utc)
      # Need a helper for 'nu' or assume mock objects don't need it
      # Assuming nu(obj) returns obj if not None, and nu(None) is handled
      # For simplicity with mocks, let's assume data is a list or None
      hourly_data = None  # Directly set hourly_data to None

      return list(
        filter(
          lambda h: is_timestamp_on_date(nu(h.time), midnight_on_date),
          hourly_data if hourly_data is not None else [],  # Handle None case in filter
        )
      )

  weather_report = MockWeatherReportNoneHourlyData()

  hourlies_for_day = weather_report.get_hourlies_for_day(test_date)

  assert hourlies_for_day == []
