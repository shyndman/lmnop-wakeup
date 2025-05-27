from collections.abc import Mapping
from typing import Any, Self, TypeVar

from pydantic import AwareDatetime, BaseModel

from lmnop_wakeup.core.typing import ensure

from ..models.hourly_data_item import HourlyDataItem

T = TypeVar("T", bound="Hourly")


class Hourly(BaseModel):
  """A block containing hour-by-hour forecasted conditions for the next 48 hours. If
  `extend=hourly` is used, the hourly block gives hour-by-hour forecasted conditions for the
  next 168 hours.

  Attributes:
      summary (None | str): A summary of the hourly forecast. Example: Light rain until this
          evening, starting again tonight.
      icon (None | str): An icon representing the hourly forecast. Example: rain.
      data (None | list['HourlyDataItem']):
  """

  summary: str | None = None
  icon: str | None = None
  data: list[HourlyDataItem] | None = None

  def trim_to_datetime(self, dt: AwareDatetime) -> Self:
    if self.data is not None:
      filtered_data = []
      for item in self.data:
        if ensure(item.local_time) > dt:
          break
        filtered_data.append(item)
      self.data = filtered_data
    return self

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
    from ..models.hourly_data_item import HourlyDataItem

    d = dict(src_dict)
    summary = d.pop("summary", None)

    icon = d.pop("icon", None)

    data = []
    _data = d.pop("data", None)
    for data_item_data in _data or []:
      data_item = HourlyDataItem.from_dict(data_item_data)

      data.append(data_item)

    hourly = cls(
      summary=summary,
      icon=icon,
      data=data,
    )

    return hourly
