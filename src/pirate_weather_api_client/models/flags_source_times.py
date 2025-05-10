from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="FlagsSourceTimes")


@_attrs_define
class FlagsSourceTimes:
  """The times in UTC when the models were last updated.

  Attributes:
      hrrr_0_18 (Unset | str): The time the HRRR model for 0-18 hours was last updated.
          Example: 2025-04-30 15Z.
      hrrr_subh (Unset | str): The time the HRRR sub-hourly model was last updated.
          Example: 2025-04-30 14Z.
      nbm (Unset | str): The time the NBM model was last updated. Example: 2025-04-29 17Z.
      nbm_fire (Unset | str): The time the NBM fire model was last updated. Example: 2025-04-30 12Z.
      hrrr_18_48 (Unset | str): The time the HRRR model for 18-48 hours was last updated.
          Example: 2025-04-30 12Z.
      gfs (Unset | str): The time the GFS model was last updated. Example: 2025-04-30 06Z.
      gefs (Unset | str): The time the GEFS model was last updated. Example: 2025-04-29 00Z.
  """

  hrrr_0_18: Unset | str = UNSET
  hrrr_subh: Unset | str = UNSET
  nbm: Unset | str = UNSET
  nbm_fire: Unset | str = UNSET
  hrrr_18_48: Unset | str = UNSET
  gfs: Unset | str = UNSET
  gefs: Unset | str = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    hrrr_0_18 = self.hrrr_0_18

    hrrr_subh = self.hrrr_subh

    nbm = self.nbm

    nbm_fire = self.nbm_fire

    hrrr_18_48 = self.hrrr_18_48

    gfs = self.gfs

    gefs = self.gefs

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if hrrr_0_18 is not UNSET:
      field_dict["hrrr_0-18"] = hrrr_0_18
    if hrrr_subh is not UNSET:
      field_dict["hrrr_subh"] = hrrr_subh
    if nbm is not UNSET:
      field_dict["nbm"] = nbm
    if nbm_fire is not UNSET:
      field_dict["nbm_fire"] = nbm_fire
    if hrrr_18_48 is not UNSET:
      field_dict["hrrr_18-48"] = hrrr_18_48
    if gfs is not UNSET:
      field_dict["gfs"] = gfs
    if gefs is not UNSET:
      field_dict["gefs"] = gefs

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    hrrr_0_18 = d.pop("hrrr_0-18", UNSET)

    hrrr_subh = d.pop("hrrr_subh", UNSET)

    nbm = d.pop("nbm", UNSET)

    nbm_fire = d.pop("nbm_fire", UNSET)

    hrrr_18_48 = d.pop("hrrr_18-48", UNSET)

    gfs = d.pop("gfs", UNSET)

    gefs = d.pop("gefs", UNSET)

    flags_source_times = cls(
      hrrr_0_18=hrrr_0_18,
      hrrr_subh=hrrr_subh,
      nbm=nbm,
      nbm_fire=nbm_fire,
      hrrr_18_48=hrrr_18_48,
      gfs=gfs,
      gefs=gefs,
    )

    flags_source_times.additional_properties = d
    return flags_source_times

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
