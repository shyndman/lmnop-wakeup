from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
  from ..models.alerts_item import AlertsItem
  from ..models.currently import Currently
  from ..models.daily import Daily
  from ..models.flags import Flags
  from ..models.hourly import Hourly
  from ..models.minutely import Minutely


T = TypeVar("T", bound="WeatherResponse200")


@_attrs_define
class WeatherResponse200:
  """
  Attributes:
      latitude (Unset | float): The requested latitude. Example: 37.3035.
      longitude (Unset | float): The requested longitude. Example: -89.523.
      timezone (Unset | str): The timezone name for the requested location.
          Example: America/Chicago.
      offset (Unset | float): The timezone offset in hours. Example: -6.
      elevation (Unset | int): The elevation in meters of the forecast point. Example: 105.
      currently (Unset | Currently): A block containing the current weather for the
          requested location.
      minutely (Unset | Minutely): A block containing minute-by-minute precipitation intensity for
          the next 60 minutes.
      hourly (Unset | Hourly): A block containing hour-by-hour forecasted conditions for the
          next 48 hours. If `extend=hourly` is used, the hourly block gives hour-by-hour forecasted
          conditions for the next 168 hours.
      daily (Unset | Daily): A block containing day-by-day forecasted conditions for the
          next 7 days.
      alerts (Unset | list['AlertsItem']): A block containing any severe weather alerts for the
          current location.
      flags (Unset | Flags): A block containing miscellaneous data for the API request.
  """

  latitude: Unset | float = UNSET
  longitude: Unset | float = UNSET
  timezone: Unset | str = UNSET
  offset: Unset | float = UNSET
  elevation: Unset | int = UNSET
  currently: Unset | Currently = UNSET
  minutely: Unset | Minutely = UNSET
  hourly: Unset | Hourly = UNSET
  daily: Unset | Daily = UNSET
  alerts: Unset | list[AlertsItem] = UNSET
  flags: Unset | Flags = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    latitude = self.latitude

    longitude = self.longitude

    timezone = self.timezone

    offset = self.offset

    elevation = self.elevation

    currently: Unset | dict[str, Any] = UNSET
    if not isinstance(self.currently, Unset):
      currently = self.currently.to_dict()

    minutely: Unset | dict[str, Any] = UNSET
    if not isinstance(self.minutely, Unset):
      minutely = self.minutely.to_dict()

    hourly: Unset | dict[str, Any] = UNSET
    if not isinstance(self.hourly, Unset):
      hourly = self.hourly.to_dict()

    daily: Unset | dict[str, Any] = UNSET
    if not isinstance(self.daily, Unset):
      daily = self.daily.to_dict()

    alerts: Unset | list[dict[str, Any]] = UNSET
    if not isinstance(self.alerts, Unset):
      alerts = []
      for componentsschemasalerts_item_data in self.alerts:
        componentsschemasalerts_item = componentsschemasalerts_item_data.to_dict()
        alerts.append(componentsschemasalerts_item)

    flags: Unset | dict[str, Any] = UNSET
    if not isinstance(self.flags, Unset):
      flags = self.flags.to_dict()

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if latitude is not UNSET:
      field_dict["latitude"] = latitude
    if longitude is not UNSET:
      field_dict["longitude"] = longitude
    if timezone is not UNSET:
      field_dict["timezone"] = timezone
    if offset is not UNSET:
      field_dict["offset"] = offset
    if elevation is not UNSET:
      field_dict["elevation"] = elevation
    if currently is not UNSET:
      field_dict["currently"] = currently
    if minutely is not UNSET:
      field_dict["minutely"] = minutely
    if hourly is not UNSET:
      field_dict["hourly"] = hourly
    if daily is not UNSET:
      field_dict["daily"] = daily
    if alerts is not UNSET:
      field_dict["alerts"] = alerts
    if flags is not UNSET:
      field_dict["flags"] = flags

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.alerts_item import AlertsItem
    from ..models.currently import Currently
    from ..models.daily import Daily
    from ..models.flags import Flags
    from ..models.hourly import Hourly
    from ..models.minutely import Minutely

    d = dict(src_dict)
    latitude = d.pop("latitude", UNSET)

    longitude = d.pop("longitude", UNSET)

    timezone = d.pop("timezone", UNSET)

    offset = d.pop("offset", UNSET)

    elevation = d.pop("elevation", UNSET)

    _currently = d.pop("currently", UNSET)
    currently: Unset | Currently
    if isinstance(_currently, Unset):
      currently = UNSET
    else:
      currently = Currently.from_dict(_currently)

    _minutely = d.pop("minutely", UNSET)
    minutely: Unset | Minutely
    if isinstance(_minutely, Unset):
      minutely = UNSET
    else:
      minutely = Minutely.from_dict(_minutely)

    _hourly = d.pop("hourly", UNSET)
    hourly: Unset | Hourly
    if isinstance(_hourly, Unset):
      hourly = UNSET
    else:
      hourly = Hourly.from_dict(_hourly)

    _daily = d.pop("daily", UNSET)
    daily: Unset | Daily
    if isinstance(_daily, Unset):
      daily = UNSET
    else:
      daily = Daily.from_dict(_daily)

    alerts = []
    _alerts = d.pop("alerts", UNSET)
    for componentsschemasalerts_item_data in _alerts or []:
      componentsschemasalerts_item = AlertsItem.from_dict(componentsschemasalerts_item_data)

      alerts.append(componentsschemasalerts_item)

    _flags = d.pop("flags", UNSET)
    flags: Unset | Flags
    if isinstance(_flags, Unset):
      flags = UNSET
    else:
      flags = Flags.from_dict(_flags)

    weather_response_200 = cls(
      latitude=latitude,
      longitude=longitude,
      timezone=timezone,
      offset=offset,
      elevation=elevation,
      currently=currently,
      minutely=minutely,
      hourly=hourly,
      daily=daily,
      alerts=alerts,
      flags=flags,
    )

    weather_response_200.additional_properties = d
    return weather_response_200

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
