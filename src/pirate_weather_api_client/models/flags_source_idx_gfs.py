from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound="FlagsSourceIDXGfs")


class FlagsSourceIDXGfs(BaseModel):
  """
  Attributes:
      x (None | int): The X coordinate for the GFS model. Example: 1082.
      y (None | int): The Y coordinate for the GFS model. Example: 509.
      lat (None | float): The latitude coordinate for the GFS model. Example: 37.25.
      long (None | float): The longitude coordinate for the GFS model. Example: -89.5.
  """

  x: None | int = None
  y: None | int = None
  lat: None | float = None
  long: None | float = None

  def to_dict(self) -> dict[str, Any]:
    x = self.x

    y = self.y

    lat = self.lat

    long = self.long

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if x is not None:
      field_dict["x"] = x
    if y is not None:
      field_dict["y"] = y
    if lat is not None:
      field_dict["lat"] = lat
    if long is not None:
      field_dict["long"] = long

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    x = d.pop("x", None)

    y = d.pop("y", None)

    lat = d.pop("lat", None)

    long = d.pop("long", None)

    flags_source_idx_gfs = cls(
      x=x,
      y=y,
      lat=lat,
      long=long,
    )

    return flags_source_idx_gfs
