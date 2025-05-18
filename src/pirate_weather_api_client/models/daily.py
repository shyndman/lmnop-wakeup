from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from ..models.daily_data_item import DailyDataItem

T = TypeVar("T", bound="Daily")


class Daily(BaseModel):
  """A block containing day-by-day forecasted conditions for the next 7 days."""

  summary: None | str = None
  """A summary of the daily forecast. Example: Drizzle tomorrow and next Wednesday, with high
  temperatures bottoming out at 21°C on Saturday."""
  icon: None | str = None
  """An icon representing the daily forecast. Example: rain."""
  data: None | list["DailyDataItem"] = None
  """A list of objects, each describing the weather of a single day"""

  def to_dict(self) -> dict[str, Any]:
    summary = self.summary

    icon = self.icon

    data: None | list[dict[str, Any]] = None
    if self.data is not None:
      data = []
      for data_item_data in self.data:
        data_item = data_item_data.to_dict()
        data.append(data_item)

    field_dict: dict[str, Any] = {}
    field_dict.update({})

    if summary is not None:
      field_dict["summary"] = summary
    if icon is not None:
      field_dict["icon"] = icon
    if data is not None:
      field_dict["data"] = data

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.daily_data_item import DailyDataItem

    d = dict(src_dict)
    summary = d.pop("summary", None)
    icon = d.pop("icon", None)

    data = []
    _data = d.pop("data", None)
    for data_item_data in _data or []:
      data_item = DailyDataItem.from_dict(data_item_data)

      data.append(data_item)

    daily = cls(
      summary=summary,
      icon=icon,
      data=data,
    )

    return daily
