from datetime import date as Date
from datetime import datetime as Datetime
from datetime import timezone
from typing import override
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel


class TimeInfo(BaseModel):
  """Represents time information, either a date or a datetime."""

  date: Date | None = None
  """The date."""
  dateTime: Datetime | None = None
  """The datetime."""
  timeZone: str | None = None
  """The timezone."""

  def to_aware_datetime(self) -> AwareDatetime:
    if self.dateTime is not None:
      if self.dateTime.tzinfo is None:
        # If dateTime is naive, assume UTC or apply timezone if available
        if self.timeZone:
          return self.dateTime.replace(tzinfo=ZoneInfo(self.timeZone))
        return self.dateTime.replace(tzinfo=timezone.utc)
      return self.dateTime

    if self.date is not None:
      # For date, assume start of the day in the specified timezone or UTC
      dt = Datetime(self.date.year, self.date.month, self.date.day, 0, 0, 0)
      if self.timeZone:
        return dt.replace(tzinfo=ZoneInfo(self.timeZone))
      return dt.replace(tzinfo=timezone.utc)

    raise ValueError("Neither 'date' nor 'dateTime' is set in TimeInfo")

  # Validate that one and only one is provided
  @override
  def model_post_init(self, __context):
    """
    Validates that either 'date' or 'dateTime' is provided, but not both.

    Args:
      __context: The validation context.

    Raises:
      ValueError: If the validation fails.
    """
    if (self.date is None and self.dateTime is None) or (
      self.date is not None and self.dateTime is not None
    ):
      raise ValueError("Either 'date' or 'dateTime' must be provided, but not both")


def format_time_info(time_info: TimeInfo, date_format: str, time_format: str) -> str:
  """
  Formats the date or datetime into a string.

  Args:
    date_format: The format for the date.
    time_format: The format for the time.

  Returns:
    A formatted string representation of the date or datetime.
  """
  if time_info.dateTime is not None:
    return time_info.dateTime.strftime(f"{date_format} {time_format}")
  if time_info.date is not None:
    return time_info.date.strftime(date_format)
  raise ValueError("Neither 'date' nor 'dateTime' is set")


def parse_date(raw: str | list[str]) -> Date:
  """
  Parses a raw string into a Date.

  Args:
    raw: The raw input string in 'YYYY-MM-DD' format.

  Returns:
    A Date instance.

  Raises:
    ValueError: If the input is a list.
  """
  if isinstance(raw, list):
    raise ValueError("List input not supported")
  return Datetime.strptime(raw, "%Y-%m-%d").date()


def to_start_of_day(dt: AwareDatetime) -> AwareDatetime:
  """Returns the start of the day in local time."""
  return dt.replace(dt.year, dt.month, dt.day, 0, 0, 0, 0)


def to_end_of_day(dt: AwareDatetime) -> AwareDatetime:
  """Returns the start of the day in local time."""
  return dt.replace(dt.year, dt.month, dt.day, 23, 59, 59, 999999)


def start_of_local_day(date: Date) -> AwareDatetime:
  """Returns the start of the provided datetime's day"""
  return to_start_of_day(Datetime.now().astimezone())


def end_of_local_day(date: Date) -> AwareDatetime:
  """Returns the end of the provided datetime's day"""
  return to_end_of_day(Datetime.now().astimezone())
