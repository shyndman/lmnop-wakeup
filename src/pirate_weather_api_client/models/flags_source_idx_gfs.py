from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import field as _attrs_field
from pydantic import BaseModel

from ..types import UNSET, Unset

T = TypeVar("T", bound="FlagsSourceIDXGfs")


class FlagsSourceIDXGfs(BaseModel):
  """
  Attributes:
      x (Unset | int): The X coordinate for the GFS model. Example: 1082.
      y (Unset | int): The Y coordinate for the GFS model. Example: 509.
      lat (Unset | float): The latitude coordinate for the GFS model. Example: 37.25.
      long (Unset | float): The longitude coordinate for the GFS model. Example: -89.5.
  """

  x: Unset | int = UNSET
  y: Unset | int = UNSET
  lat: Unset | float = UNSET
  long: Unset | float = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    x = self.x

    y = self.y

    lat = self.lat

    long = self.long

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if x is not UNSET:
      field_dict["x"] = x
    if y is not UNSET:
      field_dict["y"] = y
    if lat is not UNSET:
      field_dict["lat"] = lat
    if long is not UNSET:
      field_dict["long"] = long

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    x = d.pop("x", UNSET)

    y = d.pop("y", UNSET)

    lat = d.pop("lat", UNSET)

    long = d.pop("long", UNSET)

    flags_source_idx_gfs = cls(
      x=x,
      y=y,
      lat=lat,
      long=long,
    )

    flags_source_idx_gfs.additional_properties = d
    return flags_source_idx_gfs

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
