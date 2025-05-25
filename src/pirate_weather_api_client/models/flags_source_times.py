from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound="FlagsSourceTimes")


class FlagsSourceTimes(BaseModel):
  """The times in UTC when the models were last updated.

  Attributes:
      hrrr_0_18 (None | str): The time the HRRR model for 0-18 hours was last updated.
          Example: 2025-04-30 15Z.
      hrrr_subh (None | str): The time the HRRR sub-hourly model was last updated.
          Example: 2025-04-30 14Z.
      nbm (None | str): The time the NBM model was last updated. Example: 2025-04-29 17Z.
      nbm_fire (None | str): The time the NBM fire model was last updated. Example: 2025-04-30 12Z.
      hrrr_18_48 (None | str): The time the HRRR model for 18-48 hours was last updated.
          Example: 2025-04-30 12Z.
      gfs (None | str): The time the GFS model was last updated. Example: 2025-04-30 06Z.
      gefs (None | str): The time the GEFS model was last updated. Example: 2025-04-29 00Z.
  """

  hrrr_0_18: None | str = None
  hrrr_subh: None | str = None
  nbm: None | str = None
  nbm_fire: None | str = None
  hrrr_18_48: None | str = None
  gfs: None | str = None
  gefs: None | str = None

  def to_dict(self) -> dict[str, Any]:
    hrrr_0_18 = self.hrrr_0_18

    hrrr_subh = self.hrrr_subh

    nbm = self.nbm

    nbm_fire = self.nbm_fire

    hrrr_18_48 = self.hrrr_18_48

    gfs = self.gfs

    gefs = self.gefs

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if hrrr_0_18 is not None:
      field_dict["hrrr_0-18"] = hrrr_0_18
    if hrrr_subh is not None:
      field_dict["hrrr_subh"] = hrrr_subh
    if nbm is not None:
      field_dict["nbm"] = nbm
    if nbm_fire is not None:
      field_dict["nbm_fire"] = nbm_fire
    if hrrr_18_48 is not None:
      field_dict["hrrr_18-48"] = hrrr_18_48
    if gfs is not None:
      field_dict["gfs"] = gfs
    if gefs is not None:
      field_dict["gefs"] = gefs

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    hrrr_0_18 = d.pop("hrrr_0-18", None)

    hrrr_subh = d.pop("hrrr_subh", None)

    nbm = d.pop("nbm", None)

    nbm_fire = d.pop("nbm_fire", None)

    hrrr_18_48 = d.pop("hrrr_18-48", None)

    gfs = d.pop("gfs", None)

    gefs = d.pop("gefs", None)

    flags_source_times = cls(
      hrrr_0_18=hrrr_0_18,
      hrrr_subh=hrrr_subh,
      nbm=nbm,
      nbm_fire=nbm_fire,
      hrrr_18_48=hrrr_18_48,
      gfs=gfs,
      gefs=gefs,
    )

    return flags_source_times
