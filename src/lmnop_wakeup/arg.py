import enum
import re
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import ClassVar

from pydantic import PositiveInt
from pydantic.dataclasses import dataclass

TODAY = date.today()


class NamedRelativeDay(StrEnum):
  today = enum.auto()
  tomorrow = enum.auto()

  def resolve(self) -> date:
    if self == NamedRelativeDay.today:
      return TODAY
    elif self == NamedRelativeDay.tomorrow:
      return TODAY + timedelta(days=1)
    raise ValueError(f"Invalid named date: {self}")


@dataclass
class FutureRelativeDay:
  arg_pattern: ClassVar[re.Pattern] = re.compile(r"^\+(\d+)$")
  day_count: PositiveInt

  def __init__(self, arg: str):
    match = FutureRelativeDay.arg_pattern.match(arg)
    if not match:
      raise ValueError(f"Invalid future date argument: {arg}")
    self.day_count = int(match.group(1))

  def resolve(self) -> date:
    return TODAY + timedelta(days=self.day_count)


def parse_date(raw: str | list[str]) -> date:
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
  return datetime.strptime(raw, "%Y-%m-%d").date()


def parse_date_arg(arg: str | list[str]):
  if isinstance(arg, list):
    raise ValueError("Only one date argument is allowed")

  arg = arg.strip()
  if arg in NamedRelativeDay:
    return NamedRelativeDay(arg).resolve()

  if FutureRelativeDay.arg_pattern.match(arg):
    return FutureRelativeDay(arg).resolve()

  return parse_date(arg)
