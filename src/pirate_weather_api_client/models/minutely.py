from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from ..models.minutely_data_item import MinutelyDataItem

T = TypeVar("T", bound="Minutely")


class Minutely(BaseModel):
  """A block containing minute-by-minute precipitation intensity for the next 60 minutes.

  Attributes:
      summary (None | str): A summary of the minute-by-minute forecast. Example: Mostly
          cloudy for the hour..
      icon (None | str): An icon representing the minute-by-minute forecast.
          Example: partly-cloudy-day.
      data (None | list['MinutelyDataItem']):
  """

  summary: None | str = None
  icon: None | str = None
  data: None | list[MinutelyDataItem] = None

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
    from ..models.minutely_data_item import MinutelyDataItem

    d = dict(src_dict)
    summary = d.pop("summary", None)

    icon = d.pop("icon", None)

    data = []
    _data = d.pop("data", None)
    for data_item_data in _data or []:
      data_item = MinutelyDataItem.from_dict(data_item_data)

      data.append(data_item)

    minutely = cls(
      summary=summary,
      icon=icon,
      data=data,
    )

    return minutely
