from typing import cast

import geopy
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import GoogleV3
from haversine import Unit, haversine
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate

from ..core.typing import assert_not_none
from ..env import get_google_cloud_api_key


class GeocodeSearchResult(BaseModel):
  """
  Represents a single result from a geocoding search.

  Geocoding is the process of converting a human-readable address (like "1600 Amphitheatre Parkway,
  Mountain View, CA") into geographical coordinates (latitude and longitude) that can be used to
  pinpoint a location on a map. This class encapsulates both the precise geographical coordinates
  and the standardized, human-readable address that a geocoding service returns for a given query.

  Each `GeocodeSearchResult` provides a specific interpretation of the input address, as a single
  address query might yield multiple possible locations (e.g., "Paris" could refer to Paris, France,
  or Paris, Texas).
  """

  latlng: Coordinate
  """
  The geographical coordinates (latitude and longitude) of the geocoded location.
  """

  address: str
  """
  The human-readable, formatted address string for the geocoded location.

  This is a standardized and complete address returned by the geocoding service, which may
  differ slightly from the original input query. It provides a clear, understandable description of
  the location corresponding to the `latlng` coordinates. For instance, if the input was "Eiffel
  Tower", the address might be "Champ de Mars, 5 Av. Anatole France, 75007 Paris, France".
  """

  distance_from_user_km: float | None
  """
  The distance in kilometers from the user's home location to the geocoded location. Can be used to
  determine the correct geocode result based on the user's context.
  """


async def geocode_location(
  address: str, include_distance_from: Coordinate | None = None
) -> list[GeocodeSearchResult]:
  """
  Geocode a location using Google Maps API.

  Args:
      address (str): The address to geocode.

  Returns:
      list[GeocodeSearchResult]: A list of geocoding results for the address.
  """
  async with GoogleV3(
    api_key=get_google_cloud_api_key(), adapter_factory=AioHTTPAdapter
  ) as geolocator:
    res = await assert_not_none(geolocator.geocode(query=address, exactly_one=False))

  if res is None:
    raise ValueError(f"Could not geocode address: {address}")

  if not isinstance(res, list):
    raise TypeError(f"Expected a list of geocoding results, got {type(res)}")

  location_list = cast(list[geopy.Location], res)

  return [
    GeocodeSearchResult(
      latlng=Coordinate(latitude=location.latitude, longitude=location.longitude),
      address=location.address,
      distance_from_user_km=cast(
        float,
        haversine(
          (include_distance_from.latitude, include_distance_from.longitude),
          (location.latitude, location.longitude),
          unit=Unit.KILOMETERS,
        ),
      )
      if include_distance_from
      else None,
    )
    for location in location_list
  ]
