from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="MinutelyDataItem")


@_attrs_define
class MinutelyDataItem:
  """
  Attributes:
      time (Unset | int): The time of the data point in UNIX format. Example: 1746033120.
      precip_intensity (Unset | float): The intensity of precipitation.
      precip_probability (Unset | float): The probability of precipitation. Example: 0.14.
      precip_intensity_error (Unset | float): The standard deviation of the precipitation
          intensity. Example: 0.41.
      precip_type (Unset | str): The type of precipitation occurring. Example: none.
  """

  time: Unset | int = UNSET
  precip_intensity: Unset | float = UNSET
  precip_probability: Unset | float = UNSET
  precip_intensity_error: Unset | float = UNSET
  precip_type: Unset | str = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    time = self.time

    precip_intensity = self.precip_intensity

    precip_probability = self.precip_probability

    precip_intensity_error = self.precip_intensity_error

    precip_type = self.precip_type

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if time is not UNSET:
      field_dict["time"] = time
    if precip_intensity is not UNSET:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not UNSET:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not UNSET:
      field_dict["precipIntensityError"] = precip_intensity_error
    if precip_type is not UNSET:
      field_dict["precipType"] = precip_type

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", UNSET)

    precip_intensity = d.pop("precipIntensity", UNSET)

    precip_probability = d.pop("precipProbability", UNSET)

    precip_intensity_error = d.pop("precipIntensityError", UNSET)

    precip_type = d.pop("precipType", UNSET)

    minutely_data_item = cls(
      time=time,
      precip_intensity=precip_intensity,
      precip_probability=precip_probability,
      precip_intensity_error=precip_intensity_error,
      precip_type=precip_type,
    )

    minutely_data_item.additional_properties = d
    return minutely_data_item

  @property
  def additional_keys(self) -> list[str]:
    return list(self.additional_properties.keys())

  def __getitem__(self, key: str) -> Any:
    return self.additional_properties[key]

  def __setitem__(self, key: str, value: Any) -> None:
    self.additional_properties[key] = value

  def __delitem__(self, key: str) -> None:
    del self.additional_properties[key]

  def __contains__(self, key: str) -> bool:
    return key in self.additional_properties
