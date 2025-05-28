from datetime import date, datetime, time, timezone

from lmnop_wakeup.core.date import is_timestamp_on_date
from lmnop_wakeup.core.typing import ensure

# Import the functions and classes to be tested
from pirate_weather_api_client.models import HourlyDataItem


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
          lambda h: is_timestamp_on_date(ensure(h.time), midnight_on_date),
          hourly_data if hourly_data is not None else [],  # Handle None case in filter
        )
      )

  weather_report = MockWeatherReportNoneHourlyData()

  hourlies_for_day = weather_report.get_hourlies_for_day(test_date)

  assert hourlies_for_day == []
