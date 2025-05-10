from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import field as _attrs_field
from pydantic import BaseModel

from ..models.daily_data_item import DailyDataItem
from ..types import UNSET, Unset

T = TypeVar("T", bound="Daily")


class Daily(BaseModel):
  """A block containing day-by-day forecasted conditions for the next 7 days.

  Attributes:
      summary (Unset | str): A summary of the daily forecast. Example: Drizzle tomorrow and
          next Wednesday, with high temperatures bottoming out at 21°C on Saturday..
      icon (Unset | str): An icon representing the daily forecast. Example: rain.
      data (Unset | list['DailyDataItem']):
  """

  summary: Unset | str = UNSET
  icon: Unset | str = UNSET
  data: Unset | list["DailyDataItem"] = UNSET
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
    from ..models.daily_data_item import DailyDataItem

    d = dict(src_dict)
    summary = d.pop("summary", UNSET)

    icon = d.pop("icon", UNSET)

    data = []
    _data = d.pop("data", UNSET)
    for data_item_data in _data or []:
      data_item = DailyDataItem.from_dict(data_item_data)

      data.append(data_item)

    daily = cls(
      summary=summary,
      icon=icon,
      data=data,
    )

    daily.additional_properties = d
    return daily

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
