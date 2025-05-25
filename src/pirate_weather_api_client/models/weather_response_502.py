from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="WeatherResponse502")


@_attrs_define
class WeatherResponse502:
  """
  Attributes:
      message (None | str): The error message. Example: An invalid response was received from the
      upstream
          server.
  """

  message: None | str = None

  def to_dict(self) -> dict[str, Any]:
    message = self.message

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if message is not None:
      field_dict["message"] = message

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    message = d.pop("message", None)

    weather_response_502 = cls(
      message=message,
    )

    return weather_response_502
