import abc
from collections.abc import Iterable
from enum import StrEnum
from types import MappingProxyType
from typing import NewType, override

# from google.maps.routing import LatLng as GLatLng
from google.maps.routing import Location as GLocation
from google.maps.routing import Waypoint
from google.type.latlng_pb2 import LatLng as GLatLng
from haversine import Unit, haversine
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

LocationSlug = NewType("LocationSlug", str)
"""A unique identifier for a named location."""


class Location(BaseModel, abc.ABC):
  """
  Represents a generic location.

  This is an abstract base class for different types of locations.
  An LLM will typically instantiate either an `AddressLocation` or a `CoordinateLocation`.
  """

  @abc.abstractmethod
  def as_waypoint(self) -> Waypoint:
    """
    Converts the location to a Google Maps Waypoint object.

    Returns:
        Waypoint: The Google Maps Waypoint representation of the location.
    """
    pass

  def has_coordinates(self) -> bool:
    """
    Checks if the location has coordinates.

    Returns:
        bool: True if the location has coordinates, False otherwise.
    """
    return False


Kilometers = NewType("Kilometers", float)


class CoordinateLocation(Location):
  """
  Represents a location defined by geographical coordinates (latitude and longitude).

  An LLM may instantiate this class when a location is provided as a pair of coordinates.
  """

  latlng: Coordinate
  """The latitude and longitude of the location."""

  def __init__(self, *args, latlng: tuple[float, float], **kwargs):
    super().__init__(*args, latlng=latlng, **kwargs)  # type: ignore

  @property
  def latitude(self) -> Latitude:
    return self.latlng.latitude

  @property
  def longitude(self) -> Longitude:
    return self.latlng.longitude

  @property
  def coordinate_tuple(self) -> tuple[float, float]:
    return self.latitude, self.longitude

  def distance_to(self, other: "CoordinateLocation") -> Kilometers:
    """Calculates the distance to another coordinate location."""
    return Kilometers(
      haversine(
        self.coordinate_tuple,
        other.coordinate_tuple,
        unit=Unit.KILOMETERS,
        # The normalization and check are absoutely not necessary, but keeps this refactor proof
        normalize=True,
        check=True,
      )
    )

  @override
  def as_waypoint(self) -> Waypoint:
    """
    Converts the coordinate location to a Google Maps Waypoint object.

    Returns:
        Waypoint: The Google Maps Waypoint representation using latitude and longitude.
    """
    return Waypoint(
      location=GLocation(
        lat_lng=GLatLng(latitude=self.latitude, longitude=self.longitude),
      )
    )

  @override
  def has_coordinates(self) -> bool:
    return True


class AddressLocation(Location):
  """
  Represents a location defined by a mailing address.

  An LLM may instantiate this class when a location is provided as a mailing address. It is
  important that the address provided is fully qualified, including the city, province/state,
  postal/zip code, and country. At most, you can only be missing a couple of these details, or the
  tool will fail, and you will fail to accomplish your task.
  """

  address: str | None = None
  """The street address of the location."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  @override
  def as_waypoint(self) -> Waypoint:
    """
    Converts the address location to a Google Maps Waypoint object.

    Returns:
        Waypoint: The Google Maps Waypoint representation using the address string.
    """
    return Waypoint(address=self.address)


class ResolvedLocation(CoordinateLocation, AddressLocation):
  """
  Represents a location that has been resolved to both an address and coordinates.

  This class is typically used internally after a location (like an address) has been geocoded.
  """

  def __init__(
    self,
    *args,
    latlng: tuple[float, float],
    **kwargs,
  ):
    super().__init__(*args, **kwargs, latlng=latlng)


class NamedLocation(ResolvedLocation):
  """
  Represents a predefined, named location with a slug, description, address, and coordinates.

  An LLM will eventually be able to use a tool to retrieve instances of this class
  based on their name or slug.
  """

  name: str
  """The human-readable name of the location."""
  slug: LocationSlug
  """A unique slug identifier for the named location."""
  description: str
  """A brief description of the named location."""

  def __init__(
    self,
    *args,
    latlng: tuple[float, float],
    **kwargs,
  ):
    super().__init__(*args, **kwargs, latlng=latlng)


class LocationName(StrEnum):
  """
  Enumeration of known named locations.
  """

  clares_house = "clares_house"
  hilarys_moms_house = "hilarys_moms_house"
  home = "home"
  the_cottage = "the_cottage"
  the_farm = "the_farm"
  village_marina = "village_marina"


NAMED_LOCATIONS = MappingProxyType(
  {
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
    LocationName.the_farm: NamedLocation(
      name="The Farm",
      slug=LocationSlug("the_farm"),
      description="Where Scott's mom (Jane) and dad (Hugh) live",
      address="11923 Fifth Line, Limehouse, ON L0P 1H0",
      latlng=(43.62859507321176, -79.96554318542952),
    ),
    LocationName.village_marina: NamedLocation(
      name="Village Marina, Honey Harbour",
      slug=LocationSlug("village_marina"),
      description="Our boat is located at this harbour, which is necessary to access #the_cottage",
      address="2762 Honey Harbour Rd, Honey Harbour, ON P0E 1E0",
      latlng=(44.871795380739854, -79.8169490161212),
    ),
  }
)
"""A dictionary mapping LocationName enums to NamedLocation instances."""


def location_named(name: LocationName) -> NamedLocation:
  """
  Retrieves a predefined NamedLocation by its LocationName enum.

  Args:
      name: The LocationName enum of the desired named location.

  Returns:
      NamedLocation: The corresponding NamedLocation instance.
  """
  return NAMED_LOCATIONS[name]


class ReferencedLocations(BaseModel):
  adhoc_location_map: dict[str, Location] = {}

  def __init__(self):
    # for name, loc in _NAMED_LOCATIONS.items():
    #   self.adhoc_location_map[name.value] = loc
    pass

    # TODO: Figure out how we can integrate the persistence layer

  def add_event_location(self, possible_address: str) -> AddressLocation:
    # TODO: We have to be able to handle this, but I want to see how it happens
    if possible_address in self.adhoc_location_map:
      raise ValueError(f"Location {possible_address} already exists in the map.")
    loc = self.adhoc_location_map[possible_address] = AddressLocation(address=possible_address)
    return loc

  def all_locations(self) -> Iterable[Location]:
    return self.adhoc_location_map.values()
