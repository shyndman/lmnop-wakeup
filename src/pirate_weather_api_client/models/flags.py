from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import field as _attrs_field
from pydantic import BaseModel

from ..models.flags_source_idx import FlagsSourceIDX
from ..models.flags_source_times import FlagsSourceTimes
from ..types import UNSET, Unset

T = TypeVar("T", bound="Flags")


class Flags(BaseModel):
  """A block containing miscellaneous data for the API request.

  Attributes:
      sources (Unset | list[str]): The models used to generate the forecast.
      source_times (Unset | FlagsSourceTimes): The times in UTC when the models were last updated.
      nearest_station (Unset | int): The distance to the nearest station (not implemented,
          always returns 0).
      units (Unset | str): The units used in the forecasts. Example: ca.
      version (Unset | str): The version of Pirate Weather used to generate the forecast.
          Example: V2.6.0.
      source_idx (Unset | FlagsSourceIDX): The X, Y coordinate and the lat/long coordinate for
          each model used to generate the forecast. Only returned when version>2.
      process_time (Unset | int): The time taken to process the request in milliseconds.
          Only returned when version>2. Example: 12026.
  """

  sources: Unset | list[str] = UNSET
  source_times: Unset | FlagsSourceTimes = UNSET
  nearest_station: Unset | int = UNSET
  units: Unset | str = UNSET
  version: Unset | str = UNSET
  source_idx: Unset | FlagsSourceIDX = UNSET
  process_time: Unset | int = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    sources: Unset | list[str] = UNSET
    if not isinstance(self.sources, Unset):
      sources = self.sources

    source_times: Unset | dict[str, Any] = UNSET
    if not isinstance(self.source_times, Unset):
      source_times = self.source_times.to_dict()

    nearest_station = self.nearest_station

    units = self.units

    version = self.version

    source_idx: Unset | dict[str, Any] = UNSET
    if not isinstance(self.source_idx, Unset):
      source_idx = self.source_idx.to_dict()

    process_time = self.process_time

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if sources is not UNSET:
      field_dict["sources"] = sources
    if source_times is not UNSET:
      field_dict["sourceTimes"] = source_times
    if nearest_station is not UNSET:
      field_dict["nearest-station"] = nearest_station
    if units is not UNSET:
      field_dict["units"] = units
    if version is not UNSET:
      field_dict["version"] = version
    if source_idx is not UNSET:
      field_dict["sourceIDX"] = source_idx
    if process_time is not UNSET:
      field_dict["processTime"] = process_time

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.flags_source_idx import FlagsSourceIDX
    from ..models.flags_source_times import FlagsSourceTimes

    d = dict(src_dict)
    sources = cast(list[str], d.pop("sources", UNSET))

    _source_times = d.pop("sourceTimes", UNSET)
    source_times: Unset | FlagsSourceTimes
    if isinstance(_source_times, Unset):
      source_times = UNSET
    else:
      source_times = FlagsSourceTimes.from_dict(_source_times)

    nearest_station = d.pop("nearest-station", UNSET)

    units = d.pop("units", UNSET)

    version = d.pop("version", UNSET)

    _source_idx = d.pop("sourceIDX", UNSET)
    source_idx: Unset | FlagsSourceIDX
    if isinstance(_source_idx, Unset):
      source_idx = UNSET
    else:
      source_idx = FlagsSourceIDX.from_dict(_source_idx)

    process_time = d.pop("processTime", UNSET)

    flags = cls(
      sources=sources,
      source_times=source_times,
      nearest_station=nearest_station,
      units=units,
      version=version,
      source_idx=source_idx,
      process_time=process_time,
    )

    flags.additional_properties = d
    return flags

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
