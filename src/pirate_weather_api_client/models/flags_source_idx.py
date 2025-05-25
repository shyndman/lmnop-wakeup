from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from ..models.flags_source_idx_etopo import FlagsSourceIDXEtopo
from ..models.flags_source_idx_gfs import FlagsSourceIDXGfs
from ..models.flags_source_idx_hrrr import FlagsSourceIDXHrrr
from ..models.flags_source_idx_nbm import FlagsSourceIDXNbm

T = TypeVar("T", bound="FlagsSourceIDX")


class FlagsSourceIDX(BaseModel):
  """The X, Y coordinate and the lat/long coordinate for each model used to generate the forecast.
  Only returned when version>2.

      Attributes:
          hrrr (None | FlagsSourceIDXHrrr):
          nbm (None | FlagsSourceIDXNbm):
          gfs (None | FlagsSourceIDXGfs):
          etopo (None | FlagsSourceIDXEtopo):
  """

  hrrr: None | FlagsSourceIDXHrrr = None
  nbm: None | FlagsSourceIDXNbm = None
  gfs: None | FlagsSourceIDXGfs = None
  etopo: None | FlagsSourceIDXEtopo = None

  def to_dict(self) -> dict[str, Any]:
    hrrr: None | dict[str, Any] = None
    if self.hrrr is not None:
      hrrr = self.hrrr.to_dict()

    nbm: None | dict[str, Any] = None
    if self.nbm is not None:
      nbm = self.nbm.to_dict()

    gfs: None | dict[str, Any] = None
    if self.gfs is not None:
      gfs = self.gfs.to_dict()

    etopo: None | dict[str, Any] = None
    if self.etopo is not None:
      etopo = self.etopo.to_dict()

    field_dict: dict[str, Any] = {}
    field_dict.update({})
    if hrrr is not None:
      field_dict["hrrr"] = hrrr
    if nbm is not None:
      field_dict["nbm"] = nbm
    if gfs is not None:
      field_dict["gfs"] = gfs
    if etopo is not None:
      field_dict["etopo"] = etopo

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.flags_source_idx_etopo import FlagsSourceIDXEtopo
    from ..models.flags_source_idx_gfs import FlagsSourceIDXGfs
    from ..models.flags_source_idx_hrrr import FlagsSourceIDXHrrr
    from ..models.flags_source_idx_nbm import FlagsSourceIDXNbm

    d = dict(src_dict)
    _hrrr = d.pop("hrrr", None)
    hrrr: None | FlagsSourceIDXHrrr
    if _hrrr is None:
      hrrr = None
    else:
      hrrr = FlagsSourceIDXHrrr.from_dict(_hrrr)

    _nbm = d.pop("nbm", None)
    nbm: None | FlagsSourceIDXNbm
    if _nbm is None:
      nbm = None
    else:
      nbm = FlagsSourceIDXNbm.from_dict(_nbm)

    _gfs = d.pop("gfs", None)
    gfs: None | FlagsSourceIDXGfs
    if _gfs is None:
      gfs = None
    else:
      gfs = FlagsSourceIDXGfs.from_dict(_gfs)

    _etopo = d.pop("etopo", None)
    etopo: None | FlagsSourceIDXEtopo
    if _etopo is None:
      etopo = None
    else:
      etopo = FlagsSourceIDXEtopo.from_dict(_etopo)

    flags_source_idx = cls(
      hrrr=hrrr,
      nbm=nbm,
      gfs=gfs,
      etopo=etopo,
    )

    return flags_source_idx
