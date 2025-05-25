from collections.abc import Mapping
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from ..models.flags_source_idx import FlagsSourceIDX
from ..models.flags_source_times import FlagsSourceTimes

T = TypeVar("T", bound="Flags")


class Flags(BaseModel):
  """A block containing miscellaneous data for the API request.

  Attributes:
      sources (None | list[str]): The models used to generate the forecast.
      source_times (None | FlagsSourceTimes): The times in UTC when the models were last updated.
      nearest_station (None | int): The distance to the nearest station (not implemented,
          always returns 0).
      units (None | str): The units used in the forecasts. Example: ca.
      version (None | str): The version of Pirate Weather used to generate the forecast.
          Example: V2.6.0.
      source_idx (None | FlagsSourceIDX): The X, Y coordinate and the lat/long coordinate for
          each model used to generate the forecast. Only returned when version>2.
      process_time (None | int): The time taken to process the request in milliseconds.
          Only returned when version>2. Example: 12026.
  """

  sources: None | list[str] = None
  source_times: None | FlagsSourceTimes = None
  nearest_station: None | int = None
  units: None | str = None
  version: None | str = None
  source_idx: None | FlagsSourceIDX = None
  process_time: None | int = None

  def to_dict(self) -> dict[str, Any]:
    sources: None | list[str] = None
    if self.sources is not None:
      sources = self.sources

    source_times: None | dict[str, Any] = None
    if self.source_times is not None:
      source_times = self.source_times.to_dict()

    nearest_station = self.nearest_station

    units = self.units

    version = self.version

    source_idx: None | dict[str, Any] = None
    if self.source_idx is not None:
      source_idx = self.source_idx.to_dict()

    process_time = self.process_time

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if sources is not None:
      field_dict["sources"] = sources
    if source_times is not None:
      field_dict["sourceTimes"] = source_times
    if nearest_station is not None:
      field_dict["nearest-station"] = nearest_station
    if units is not None:
      field_dict["units"] = units
    if version is not None:
      field_dict["version"] = version
    if source_idx is not None:
      field_dict["sourceIDX"] = source_idx
    if process_time is not None:
      field_dict["processTime"] = process_time

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.flags_source_idx import FlagsSourceIDX
    from ..models.flags_source_times import FlagsSourceTimes

    d = dict(src_dict)
    sources = cast(list[str], d.pop("sources", None))

    _source_times = d.pop("sourceTimes", None)
    source_times: None | FlagsSourceTimes
    if _source_times is None:
      source_times = None
    else:
      source_times = FlagsSourceTimes.from_dict(_source_times)

    nearest_station = d.pop("nearest-station", None)

    units = d.pop("units", None)

    version = d.pop("version", None)

    _source_idx = d.pop("sourceIDX", None)
    source_idx: None | FlagsSourceIDX
    if _source_idx is None:
      source_idx = None
    else:
      source_idx = FlagsSourceIDX.from_dict(_source_idx)

    process_time = d.pop("processTime", None)

    flags = cls(
      sources=sources,
      source_times=source_times,
      nearest_station=nearest_station,
      units=units,
      version=version,
      source_idx=source_idx,
      process_time=process_time,
    )

    return flags
