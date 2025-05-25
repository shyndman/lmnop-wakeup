from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

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
      latitude (None | float): The requested latitude. Example: 37.3035.
      longitude (None | float): The requested longitude. Example: -89.523.
      timezone (None | str): The timezone name for the requested location.
          Example: America/Chicago.
      offset (None | float): The timezone offset in hours. Example: -6.
      elevation (None | int): The elevation in meters of the forecast point. Example: 105.
      currently (None | Currently): A block containing the current weather for the
          requested location.
      minutely (None | Minutely): A block containing minute-by-minute precipitation intensity for
          the next 60 minutes.
      hourly (None | Hourly): A block containing hour-by-hour forecasted conditions for the
          next 48 hours. If `extend=hourly` is used, the hourly block gives hour-by-hour forecasted
          conditions for the next 168 hours.
      daily (None | Daily): A block containing day-by-day forecasted conditions for the
          next 7 days.
      alerts (None | list['AlertsItem']): A block containing any severe weather alerts for the
          current location.
      flags (None | Flags): A block containing miscellaneous data for the API request.
  """

  latitude: None | float = None
  longitude: None | float = None
  timezone: None | str = None
  offset: None | float = None
  elevation: None | int = None
  currently: None | Currently = None
  minutely: None | Minutely = None
  hourly: None | Hourly = None
  daily: None | Daily = None
  alerts: None | list[AlertsItem] = None
  flags: None | Flags = None

  def to_dict(self) -> dict[str, Any]:
    latitude = self.latitude

    longitude = self.longitude

    timezone = self.timezone

    offset = self.offset

    elevation = self.elevation

    currently: None | dict[str, Any] = None
    if self.currently is not None:
      currently = self.currently.to_dict()

    minutely: None | dict[str, Any] = None
    if self.minutely is not None:
      minutely = self.minutely.to_dict()

    hourly: None | dict[str, Any] = None
    if self.hourly is not None:
      hourly = self.hourly.to_dict()

    daily: None | dict[str, Any] = None
    if self.daily is not None:
      daily = self.daily.to_dict()

    alerts: None | list[dict[str, Any]] = None
    if self.alerts is not None:
      alerts = []
      for componentsschemasalerts_item_data in self.alerts:
        componentsschemasalerts_item = componentsschemasalerts_item_data.to_dict()
        alerts.append(componentsschemasalerts_item)

    flags: None | dict[str, Any] = None
    if self.flags is not None:
      flags = self.flags.to_dict()

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if latitude is not None:
      field_dict["latitude"] = latitude
    if longitude is not None:
      field_dict["longitude"] = longitude
    if timezone is not None:
      field_dict["timezone"] = timezone
    if offset is not None:
      field_dict["offset"] = offset
    if elevation is not None:
      field_dict["elevation"] = elevation
    if currently is not None:
      field_dict["currently"] = currently
    if minutely is not None:
      field_dict["minutely"] = minutely
    if hourly is not None:
      field_dict["hourly"] = hourly
    if daily is not None:
      field_dict["daily"] = daily
    if alerts is not None:
      field_dict["alerts"] = alerts
    if flags is not None:
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
    latitude = d.pop("latitude", None)

    longitude = d.pop("longitude", None)

    timezone = d.pop("timezone", None)

    offset = d.pop("offset", None)

    elevation = d.pop("elevation", None)

    _currently = d.pop("currently", None)
    currently: None | Currently
    if _currently is None:
      currently = None
    else:
      currently = Currently.from_dict(_currently)

    _minutely = d.pop("minutely", None)
    minutely: None | Minutely
    if _minutely is None:
      minutely = None
    else:
      minutely = Minutely.from_dict(_minutely)

    _hourly = d.pop("hourly", None)
    hourly: None | Hourly
    if _hourly is None:
      hourly = None
    else:
      hourly = Hourly.from_dict(_hourly)

    _daily = d.pop("daily", None)
    daily: None | Daily
    if _daily is None:
      daily = None
    else:
      daily = Daily.from_dict(_daily)

    alerts = []
    _alerts = d.pop("alerts", None)
    for componentsschemasalerts_item_data in _alerts or []:
      componentsschemasalerts_item = AlertsItem.from_dict(componentsschemasalerts_item_data)

      alerts.append(componentsschemasalerts_item)

    _flags = d.pop("flags", None)
    flags: None | Flags
    if _flags is None:
      flags = None
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

    return weather_response_200
