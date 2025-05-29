import abc
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, NewType, override

# from google.maps.routing import LatLng as GLatLng
from google.maps.routing import Location as GLocation
from google.maps.routing import Waypoint
from google.type.latlng_pb2 import LatLng as GLatLng
from haversine import Unit, haversine
from pydantic import BaseModel, ConfigDict
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

LocationSlug = NewType("LocationSlug", str)
"""A unique identifier for a named location."""


class Location(BaseModel, abc.ABC):
  """
  Represents a generic location.

  This is an abstract base class for different types of locations.
  An LLM will typically instantiate either an `AddressLocation` or a `CoordinateLocation`.
  """

  model_config = ConfigDict(frozen=True)

  @abc.abstractmethod
  def as_waypoint(self) -> Waypoint:
    """
    Converts the location to a Google Maps Waypoint object.

    Returns:
        Waypoint: The Google Maps Waypoint representation of the location.
    """
    pass

  if TYPE_CHECKING:

    @override
    def __hash__(self) -> int: ...


Kilometers = NewType("Kilometers", float)


class CoordinateLocation(Location):
  """
  Represents a location defined by geographical coordinates (latitude and longitude).

  An LLM may instantiate this class when a location is provided as a pair of coordinates.
  """

  model_config = ConfigDict(frozen=True)

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

  if TYPE_CHECKING:

    @override
    def __hash__(self) -> int: ...


class ResolvedLocation(CoordinateLocation):
  """
  Represents a location that has been resolved to both an address and coordinates.

  This class is typically used internally after a location (like an address) has been geocoded.
  """

  model_config = ConfigDict(frozen=True)

  address: str

  def __init__(
    self,
    *args,
    latlng: tuple[float, float],
    **kwargs,
  ):
    super().__init__(*args, **kwargs, latlng=latlng)

  @property
  def label(self) -> str:
    return self.address

  if TYPE_CHECKING:

    @override
    def __hash__(self) -> int: ...


class NamedLocation(ResolvedLocation):
  """
  Represents a predefined, named location with a slug, description, address, and coordinates.

  An LLM will eventually be able to use a tool to retrieve instances of this class
  based on their name or slug.
  """

  model_config = ConfigDict(frozen=True)

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

  @property
  @override
  def label(self) -> str:
    return self.name

  if TYPE_CHECKING:

    @override
    def __hash__(self) -> int: ...


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
      address="",
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

  def __add__(self, other: "ReferencedLocations") -> "ReferencedLocations":
    """
    Merge a referenced locations with the receiver, and returns a new referenced locations as
    the result.

    Args:
        other (ResolvedLocation): The resolved location to add.

    Returns:
        ReferencedLocations: The updated instance with the new location added.
    """
    if not isinstance(other, ReferencedLocations):
      raise TypeError("Can only add another ReferencedLocations instance.")

    new_map = self.adhoc_location_map.copy()
    new_map.update(other.adhoc_location_map)
    return ReferencedLocations(adhoc_location_map=new_map)
