from collections.abc import Mapping
from datetime import datetime
from typing import Any, TypeVar, cast

from pydantic import AwareDatetime, BaseModel, computed_field

T = TypeVar("T", bound="AlertsItem")


class AlertsItem(BaseModel):
  """
  Attributes:
      title (None | str): A brief description of the alert. Example: Flood Warning.
      regions (None | list[str]): An array of strings containing all regions included in the
            weather alert.
      severity (None | str): The severity of the weather alert. Example: Severe.
      time (None | int]): The time the alert was issued in UNIX format. Example: 1715357220.
      expires (None | int]): The time the alert expires in UNIX format. Example: 1715451300.
      description (None | str): A detailed description of the alert. Example:

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
        (None | str): A HTTP(S) URL for more information about the alert. Example:
        https://alerts.weather.gov/search?id=urn:oid:2.49.0.1.840.0.f24c2a5f205f53c0f443861ac62244cc6aecfc9c.002.1.
  """

  title: None | str = None
  regions: None | list[str] = None
  severity: None | str = None
  time: None | int = None
  expires: None | int = None
  description: None | str = None
  uri: None | str = None

  @computed_field
  @property
  def local_time(self) -> AwareDatetime | None:
    if self.time is None:
      return None
    else:
      return datetime.fromtimestamp(self.time).astimezone()

  @computed_field
  @property
  def local_expires(self) -> AwareDatetime | None:
    if self.expires is None:
      return None
    else:
      return datetime.fromtimestamp(self.expires).astimezone()

  def to_dict(self) -> dict[str, Any]:
    title = self.title

    regions: None | list[str] = None
    regions = self.regions

    severity = self.severity

    time = self.time

    expires = self.expires

    description = self.description

    uri = self.uri

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if title is not None:
      field_dict["title"] = title
    if regions is not None:
      field_dict["regions"] = regions
    if severity is not None:
      field_dict["severity"] = severity
    if time is not None:
      field_dict["time"] = time
    if expires is not None:
      field_dict["expires"] = expires
    if description is not None:
      field_dict["description"] = description
    if uri is not None:
      field_dict["uri"] = uri

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    title = d.pop("title", None)

    regions = cast(list[str], d.pop("regions", None))

    severity = d.pop("severity", None)

    time = d.pop("time", None)

    expires = d.pop("expires", None)

    description = d.pop("description", None)

    uri = d.pop("uri", None)

    alerts_item = cls(
      title=title,
      regions=regions,
      severity=severity,
      time=time,
      expires=expires,
      description=description,
      uri=uri,
    )

    return alerts_item
