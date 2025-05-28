from typing import cast

import geopy
from geopy.geocoders import GoogleV3
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate

from lmnop_wakeup.core.typing import assert_not_none

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

  Latitude specifies the north-south position of a point on the Earth's surface,
  while longitude specifies the east-west position. Together, they form a unique
  point that can be plotted on a map. For example, 37.4220 latitude and -122.0841 longitude
  point to Google's headquarters in Mountain View, California.
  """

  address: str
  """
  The human-readable, formatted address string for the geocoded location.

  This is typically a standardized and complete address returned by the geocoding service, which may
  differ slightly from the original input query. It provides a clear, understandable description of
  the location corresponding to the `latlng` coordinates. For instance, if the input was "Eiffel
  Tower", the address might be "Champ de Mars, 5 Av. Anatole France, 75007 Paris, France".
  """


async def geocode_location(address: str) -> list[GeocodeSearchResult]:
  """
  Geocode a location using Google Maps API.

  Args:
      address (str): The address to geocode.

  Returns:
      list[GeocodeSearchResult]: A list of geocoding results for the address.
  """
  geolocator = GoogleV3(api_key=get_google_cloud_api_key())
  res = await assert_not_none(geolocator.geocode(query=address))

  if res is None:
    raise ValueError(f"Could not geocode address: {address}")

  if not isinstance(list, res):
    raise TypeError(f"Expected a list of geocoding results, got {type(res)}")

  location_list = cast(list[geopy.Location], res)

  return [
    GeocodeSearchResult(
      latlng=Coordinate(latitude=location.latitude, longitude=location.longitude),
      address=location.address,
    )
    for location in location_list
  ]
