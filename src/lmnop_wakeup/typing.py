from typing import TypeVar, cast

from pirate_weather_api_client.types import Unset

T = TypeVar("T")


def assert_not_none(val: T | None) -> T:
  if val is None:
    raise ValueError("Value is None: {}", val)
  return val


def nn(val: T | None) -> T:
  return cast(T, val)


def nu(val: T | Unset) -> T:
  return cast(T, val)
