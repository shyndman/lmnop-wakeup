from datetime import date as Date
from datetime import datetime as DateTime
from typing import override

from pydantic import AwareDatetime, BaseModel


class TimeInfo(BaseModel):
  """Represents time information, either a date or a datetime."""

  date: Date | None = None
  """The date."""
  dateTime: DateTime | None = None
  """The datetime."""
  timeZone: str | None = None
  """The timezone."""

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
  return DateTime.strptime(raw, "%Y-%m-%d").date()


def start_of_local_day(date: Date) -> AwareDatetime:
  """Returns the start of the day in local time."""
  dt = DateTime.now().astimezone()
  return dt.replace(date.year, date.month, date.day, 0, 0, 0)


def end_of_local_day(date: Date) -> AwareDatetime:
  """Returns the start of the day in local time."""
  dt = DateTime.now().astimezone()
  return dt.replace(date.year, date.month, date.day, 0, 0, 0)
