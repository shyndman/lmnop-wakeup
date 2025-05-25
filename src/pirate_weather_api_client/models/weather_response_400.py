from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="WeatherResponse400")


@_attrs_define
class WeatherResponse400:
  """
  Attributes:
      detail (None | str): The error message Example: Invalid Location Specification.
  """

  detail: None | str = None

  def to_dict(self) -> dict[str, Any]:
    detail = self.detail

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if detail is not None:
      field_dict["detail"] = detail

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    detail = d.pop("detail", None)

    weather_response_400 = cls(
      detail=detail,
    )

    return weather_response_400
