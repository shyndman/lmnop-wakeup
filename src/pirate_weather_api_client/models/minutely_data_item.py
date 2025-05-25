from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound="MinutelyDataItem")


class MinutelyDataItem(BaseModel):
  """
  Attributes:
      time (None | int): The time of the data point in UNIX format. Example: 1746033120.
      precip_intensity (None | float): The intensity of precipitation.
      precip_probability (None | float): The probability of precipitation. Example: 0.14.
      precip_intensity_error (None | float): The standard deviation of the precipitation
          intensity. Example: 0.41.
      precip_type (None | str): The type of precipitation occurring. Example: none.
  """

  time: None | int = None
  precip_intensity: None | float = None
  precip_probability: None | float = None
  precip_intensity_error: None | float = None
  precip_type: None | str = None

  def to_dict(self) -> dict[str, Any]:
    time = self.time

    precip_intensity = self.precip_intensity

    precip_probability = self.precip_probability

    precip_intensity_error = self.precip_intensity_error

    precip_type = self.precip_type

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if time is not None:
      field_dict["time"] = time
    if precip_intensity is not None:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not None:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not None:
      field_dict["precipIntensityError"] = precip_intensity_error
    if precip_type is not None:
      field_dict["precipType"] = precip_type

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", None)

    precip_intensity = d.pop("precipIntensity", None)

    precip_probability = d.pop("precipProbability", None)

    precip_intensity_error = d.pop("precipIntensityError", None)

    precip_type = d.pop("precipType", None)

    minutely_data_item = cls(
      time=time,
      precip_intensity=precip_intensity,
      precip_probability=precip_probability,
      precip_intensity_error=precip_intensity_error,
      precip_type=precip_type,
    )

    return minutely_data_item
