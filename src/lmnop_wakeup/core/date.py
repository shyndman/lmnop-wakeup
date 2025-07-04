from datetime import date as Date
from datetime import datetime, time, timezone
from datetime import datetime as Datetime
from typing import overload, override
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, field_serializer


def is_timestamp_on_date(ts: int, midnight_on_date: datetime) -> bool:
  date_to_check = datetime.fromtimestamp(ts, tz=midnight_on_date.tzinfo)
  return date_to_check.date() == midnight_on_date.date()


class TimeInfo(BaseModel):
  """Represents time information, either a date or a datetime."""

  date: Date | None = None
  """The date."""

  dateTime: Datetime | None = None
  """The datetime."""

  timeZone: str | None = None
  """The timezone."""

  @field_serializer("date")
  def serialize_date(self, v: Date, _info):
    return v.isoformat() if v else None

  @field_serializer("dateTime")
  def serialize_dateTime(self, v: Datetime, _info):
    return v.isoformat() if v else None

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


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


@overload
def start_of_local_day(dt: AwareDatetime) -> AwareDatetime:
  """Returns the start of the day in local time."""
  ...


@overload
def start_of_local_day(dt: Date) -> AwareDatetime:
  """Returns the start of the provided datetime's day"""
  ...


@overload
def end_of_local_day(dt: AwareDatetime) -> AwareDatetime:
  """Returns the start of the day in local time."""
  ...


@overload
def end_of_local_day(dt: Date) -> AwareDatetime:
  """Returns the end of the provided datetime's day"""
  ...


def start_of_local_day(dt) -> AwareDatetime:
  if isinstance(dt, Date):
    return Datetime.combine(dt, time.min, tzinfo=LOCAL_TIMEZONE)

  return dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=LOCAL_TIMEZONE)


def end_of_local_day(dt) -> AwareDatetime:
  if isinstance(dt, Date):
    return Datetime.combine(dt, time.max, tzinfo=LOCAL_TIMEZONE)

  return dt.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=LOCAL_TIMEZONE)


def get_ordinal_suffix(day: int) -> str:
  """Get the ordinal suffix for a day number (e.g., 1 -> 'st', 2 -> 'nd')."""
  if 11 <= day <= 13:
    return "th"
  suffix_map = {1: "st", 2: "nd", 3: "rd"}
  return suffix_map.get(day % 10, "th")
