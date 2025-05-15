import abc
from enum import StrEnum
from typing import NewType, override

# from google.maps.routing import LatLng as GLatLng
from google.maps.routing import Location as GLocation
from google.maps.routing import Waypoint
from google.type.latlng_pb2 import LatLng as GLatLng
from pydantic import BaseModel

LocationSlug = NewType("LocationSlug", str)


class Location(BaseModel, abc.ABC):
  @abc.abstractmethod
  def as_waypoint(self) -> Waypoint:
    pass


class CoordinateLocation(Location):
  latlng: tuple[float, float]

  @override
  def as_waypoint(self) -> Waypoint:
    return Waypoint(
      location=GLocation(
        lat_lng=GLatLng(latitude=self.latlng[0], longitude=self.latlng[1]),
      )
    )


class AddressLocation(Location):
  address: str | None = None

  @override
  def as_waypoint(self) -> Waypoint:
    return Waypoint(address=self.address)


class ResolvedLocation(CoordinateLocation, AddressLocation):
  pass


class NamedLocation(ResolvedLocation):
  name: str
  slug: LocationSlug
  description: str


class LocationName(StrEnum):
  home = "home"
  the_cottage = "the_cottage"
  village_marina = "village_marina"
  clares_house = "clares_house"
  hilarys_moms_house = "hilarys_moms_house"
  the_farm = "the_farm"


NAMED_LOCATIONS = {
  LocationName.home: NamedLocation(
    name="Home",
    slug=LocationSlug("home"),
    description="Our little bungalow in Toronto",
    address="16 Doncaster Ave, East York, ON M4C 1Y5",
    latlng=(43.69107214185943, -79.3077542870965),
  ),
  LocationName.the_cottage: NamedLocation(
    name="The Cottage",
    slug=LocationSlug("the_cottage"),
    description="Our family cottage, situated on a small island, accessible only by boat. "
    "We park our car at #village_marina",
    latlng=(44.89267017178425, -79.87324555175594),
  ),
  LocationName.village_marina: NamedLocation(
    name="Village Marina, Honey Harbour",
    slug=LocationSlug("village_marina"),
    description="Our boat is located at this harbour, which is necessary to access #the_cottage",
    address="2762 Honey Harbour Rd, Honey Harbour, ON P0E 1E0",
    latlng=(44.871795380739854, -79.8169490161212),
  ),
  LocationName.clares_house: NamedLocation(
    name="Clare's House",
    slug=LocationSlug("clares_house"),
    description="Hilary's sister Clare and her nephew Raines live here",
    address="25 Boston Ave, Toronto, ON M4M 2T8",
    latlng=(43.662295739811015, -79.33893969395115),
  ),
  LocationName.hilarys_moms_house: NamedLocation(
    name="Hilary's Mom's House",
    slug=LocationSlug("hilarys_mom_house"),
    description="Where Hilary's mom (Barb) and her step dad Dale live",
    address="20 Glebe Rd W, Toronto, ON M4S 1Z9",
    latlng=(43.70085281487342, -79.39773088140363),
  ),
  LocationName.the_farm: NamedLocation(
    name="The Farm",
    slug=LocationSlug("the_farm"),
    description="Where Scott's mom (Jane) and dad (Hugh) live",
    address="11923 Fifth Line, Limehouse, ON L0P 1H0",
    latlng=(43.62859507321176, -79.96554318542952),
  ),
}


def location_named(name: LocationName) -> NamedLocation:
  return NAMED_LOCATIONS[name]
