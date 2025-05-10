from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
  from ..models.flags_source_idx_etopo import FlagsSourceIDXEtopo
  from ..models.flags_source_idx_gfs import FlagsSourceIDXGfs
  from ..models.flags_source_idx_hrrr import FlagsSourceIDXHrrr
  from ..models.flags_source_idx_nbm import FlagsSourceIDXNbm


T = TypeVar("T", bound="FlagsSourceIDX")


@_attrs_define
class FlagsSourceIDX:
  """The X, Y coordinate and the lat/long coordinate for each model used to generate the forecast.
  Only returned when version>2.

      Attributes:
          hrrr (Unset | FlagsSourceIDXHrrr):
          nbm (Unset | FlagsSourceIDXNbm):
          gfs (Unset | FlagsSourceIDXGfs):
          etopo (Unset | FlagsSourceIDXEtopo):
  """

  hrrr: Unset | FlagsSourceIDXHrrr = UNSET
  nbm: Unset | FlagsSourceIDXNbm = UNSET
  gfs: Unset | FlagsSourceIDXGfs = UNSET
  etopo: Unset | FlagsSourceIDXEtopo = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    hrrr: Unset | dict[str, Any] = UNSET
    if not isinstance(self.hrrr, Unset):
      hrrr = self.hrrr.to_dict()

    nbm: Unset | dict[str, Any] = UNSET
    if not isinstance(self.nbm, Unset):
      nbm = self.nbm.to_dict()

    gfs: Unset | dict[str, Any] = UNSET
    if not isinstance(self.gfs, Unset):
      gfs = self.gfs.to_dict()

    etopo: Unset | dict[str, Any] = UNSET
    if not isinstance(self.etopo, Unset):
      etopo = self.etopo.to_dict()

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if hrrr is not UNSET:
      field_dict["hrrr"] = hrrr
    if nbm is not UNSET:
      field_dict["nbm"] = nbm
    if gfs is not UNSET:
      field_dict["gfs"] = gfs
    if etopo is not UNSET:
      field_dict["etopo"] = etopo

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    from ..models.flags_source_idx_etopo import FlagsSourceIDXEtopo
    from ..models.flags_source_idx_gfs import FlagsSourceIDXGfs
    from ..models.flags_source_idx_hrrr import FlagsSourceIDXHrrr
    from ..models.flags_source_idx_nbm import FlagsSourceIDXNbm

    d = dict(src_dict)
    _hrrr = d.pop("hrrr", UNSET)
    hrrr: Unset | FlagsSourceIDXHrrr
    if isinstance(_hrrr, Unset):
      hrrr = UNSET
    else:
      hrrr = FlagsSourceIDXHrrr.from_dict(_hrrr)

    _nbm = d.pop("nbm", UNSET)
    nbm: Unset | FlagsSourceIDXNbm
    if isinstance(_nbm, Unset):
      nbm = UNSET
    else:
      nbm = FlagsSourceIDXNbm.from_dict(_nbm)

    _gfs = d.pop("gfs", UNSET)
    gfs: Unset | FlagsSourceIDXGfs
    if isinstance(_gfs, Unset):
      gfs = UNSET
    else:
      gfs = FlagsSourceIDXGfs.from_dict(_gfs)

    _etopo = d.pop("etopo", UNSET)
    etopo: Unset | FlagsSourceIDXEtopo
    if isinstance(_etopo, Unset):
      etopo = UNSET
    else:
      etopo = FlagsSourceIDXEtopo.from_dict(_etopo)

    flags_source_idx = cls(
      hrrr=hrrr,
      nbm=nbm,
      gfs=gfs,
      etopo=etopo,
    )

    flags_source_idx.additional_properties = d
    return flags_source_idx

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
