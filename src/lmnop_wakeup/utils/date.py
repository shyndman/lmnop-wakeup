from datetime import date, datetime

from pydantic import AwareDatetime


def start_of_local_day(date: date) -> AwareDatetime:
  """Returns the start of the day in local time."""
  dt = datetime.now().astimezone()
  return dt.replace(date.year, date.month, date.day, 0, 0, 0)


def end_of_local_day(date: date) -> AwareDatetime:
  """Returns the start of the day in local time."""
  dt = datetime.now().astimezone()
  return dt.replace(date.year, date.month, date.day, 0, 0, 0)
