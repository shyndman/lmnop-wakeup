from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from pydantic import BaseModel

from ..types import UNSET, Unset

T = TypeVar("T", bound="AlertsItem")


@_attrs_define
class AlertsItem(BaseModel):
  """
  Attributes:
      title (Unset | str): A brief description of the alert. Example: Flood Warning.
      regions (Unset | list[str]): An array of strings containing all regions included in the
            weather alert.
      severity (Unset | str): The severity of the weather alert. Example: Severe.
      time (Unset | int]): The time the alert was issued in UNIX format. Example: 1715357220.
      expires (Unset | int]): The time the alert expires in UNIX format. Example: 1715451300.
      description (Unset | str): A detailed description of the alert. Example:

            ...The Flood Warning is extended for the following river in Illinois...Missouri
            ...Kentucky... Mississippi River at Cape Girardeau, Thebes, and Hickman. With
            recent heavy rainfall, waters are rising on the Mississippi River with crests in minor
            flood at Cape Girardeau, Thebes, and Hickman early next week.  For the Mississippi
            River...including Cape Girardeau, Thebes, Hickman...Minor flooding is forecast.

            * WHAT...Minor flooding is occurring and minor flooding is forecast.
            * WHERE...Mississippi River at Cape Girardeau.
            * WHEN...Until Friday, May 17.
            * IMPACTS...At 36.0 feet, The flood gate on Themis Street closes.
            * ADDITIONAL DETAILS... - At 11:00 AM CDT Friday the stage was 34.4 feet.

    - Forecast...The river is expected to rise to a crest of 36.0 feet Monday morning. It will
        then fall below flood stage late Thursday evening. - Flood stage is 32.0 feet.. uri
        (Unset | str): A HTTP(S) URL for more information about the alert. Example:
        https://alerts.weather.gov/search?id=urn:oid:2.49.0.1.840.0.f24c2a5f205f53c0f443861ac62244cc6aecfc9c.002.1.
  """

  title: Unset | str = UNSET
  regions: Unset | list[str] = UNSET
  severity: Unset | str = UNSET
  time: Unset | int = UNSET
  expires: Unset | int = UNSET
  description: Unset | str = UNSET
  uri: Unset | str = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    title = self.title

    regions: Unset | list[str] = UNSET
    if not isinstance(self.regions, Unset):
      regions = self.regions

    severity = self.severity

    time = self.time

    expires = self.expires

    description = self.description

    uri = self.uri

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if title is not UNSET:
      field_dict["title"] = title
    if regions is not UNSET:
      field_dict["regions"] = regions
    if severity is not UNSET:
      field_dict["severity"] = severity
    if time is not UNSET:
      field_dict["time"] = time
    if expires is not UNSET:
      field_dict["expires"] = expires
    if description is not UNSET:
      field_dict["description"] = description
    if uri is not UNSET:
      field_dict["uri"] = uri

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    title = d.pop("title", UNSET)

    regions = cast(list[str], d.pop("regions", UNSET))

    severity = d.pop("severity", UNSET)

    time = d.pop("time", UNSET)

    expires = d.pop("expires", UNSET)

    description = d.pop("description", UNSET)

    uri = d.pop("uri", UNSET)

    alerts_item = cls(
      title=title,
      regions=regions,
      severity=severity,
      time=time,
      expires=expires,
      description=description,
      uri=uri,
    )

    alerts_item.additional_properties = d
    return alerts_item

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
