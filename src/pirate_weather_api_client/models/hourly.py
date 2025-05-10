from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from pydantic import BaseModel

from ..types import UNSET, Unset

if TYPE_CHECKING:
  from ..models.hourly_data_item import HourlyDataItem


T = TypeVar("T", bound="Hourly")


@_attrs_define
class Hourly(BaseModel):
  """A block containing hour-by-hour forecasted conditions for the next 48 hours. If
  `extend=hourly` is used, the hourly block gives hour-by-hour forecasted conditions for the
  next 168 hours.

  Attributes:
      summary (Unset | str): A summary of the hourly forecast. Example: Light rain until this
          evening, starting again tonight.
      icon (Unset | str): An icon representing the hourly forecast. Example: rain.
      data (Unset | list['HourlyDataItem']):
  """

  summary: Unset | str = UNSET
  icon: Unset | str = UNSET
  data: Unset | list[HourlyDataItem] = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    summary = self.summary

    icon = self.icon

    data: Unset | list[dict[str, Any]] = UNSET
    if not isinstance(self.data, Unset):
      data = []
      for data_item_data in self.data:
        data_item = data_item_data.to_dict()
        data.append(data_item)

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if summary is not UNSET:
      field_dict["summary"] = summary
    if icon is not UNSET:
      field_dict["icon"] = icon
    if data is not UNSET:
      field_dict["data"] = data

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.hourly_data_item import HourlyDataItem

    d = dict(src_dict)
    summary = d.pop("summary", UNSET)

    icon = d.pop("icon", UNSET)

    data = []
    _data = d.pop("data", UNSET)
    for data_item_data in _data or []:
      data_item = HourlyDataItem.from_dict(data_item_data)

      data.append(data_item)

    hourly = cls(
      summary=summary,
      icon=icon,
      data=data,
    )

    hourly.additional_properties = d
    return hourly

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
