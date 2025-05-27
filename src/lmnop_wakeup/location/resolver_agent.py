from collections.abc import Callable
from typing import override

import lazy_object_proxy
from pydantic import BaseModel

from ..core.typing import ensure
from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName
from .geocode_api import GeocodeSearchResult, geocode_location
from .model import AddressLocation, CoordinateLocation, NamedLocation


class LocationResolverInput(LangfuseAgentInput):
  """Input for the location resolver agent."""

  home_location: NamedLocation
  """The user's home location, where they begin their day"""
  named_locations: list[NamedLocation]
  """Special locations for the user, that are referenced by shorter titles"""
  location: AddressLocation
  """The location to resolve."""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "location": ensure(self.location.address),
      "home_location": self.home_location.model_dump_json(),
      "named_locations": "\n".join([f" * {location.name}" for location in self.named_locations]),
    }


class ResolutionFailure(BaseModel):
  """Indicates failure to resolve a location"""

  failure_reason: str | None = None
  """If no location could be determined, this field should contain a reason for the failure."""


class LocationResolverOutput(BaseModel):
  """Output for the location resolver agent."""

  location: NamedLocation | CoordinateLocation | ResolutionFailure
  """Set to the NamedLocation, if the input location was identified as one of the user's named
  locations, or a CoordinateLocation returned by the geocode tool.

  If no location could be determined, set this value to a ResolutionFailure instance, describing
  the problem."""


type LocationResolverAgent = LangfuseAgent[LocationResolverInput, LocationResolverOutput]


def _get_location_resolver_agent() -> LocationResolverAgent:
  """Get the location resolver agent."""

  agent = LangfuseAgent[LocationResolverInput, LocationResolverOutput].create(
    "location_resolver",
    model=ModelName.GEMINI_20_FLASH_LITE,
    input_type=LocationResolverInput,
    output_type=LocationResolverOutput,
  )

  @agent.tool_plain
  async def geocode(location: str) -> list[GeocodeSearchResult]:
    """
    Geocode a location string, such as an address or the name of a place, to its precise geographic
    coordinates.

    Geocoding is the process of transforming a human-readable address or place name (like "Eiffel
    Tower, Paris" or "1600 Amphitheatre Parkway, Mountain View, CA") into a set of geographical
    coordinates, specifically latitude and longitude. These coordinates are numerical values that
    pinpoint a unique location on the Earth's surface.

    This tool acts as an interface to a geocoding service, allowing the system to understand and
    process natural language location queries. It converts these queries into a format that can be
    used for mapping, navigation, or any location-based service.

    Args:
      location (str): The location string to be geocoded. This input is flexible and can include:
        - A complete street address (e.g., "1600 Amphitheatre Parkway, Mountain View, CA, USA")
        - A partial address, which the service will attempt to resolve (e.g., "Eiffel Tower, Paris")
        - The name of a well-known landmark or place (e.g., "Central Park", "Golden Gate Bridge")
        - A combination of city and country (e.g., "London, UK")
        The more specific the input, the more accurate and precise the geocoding result is likely to
        be.

    Returns:
      list[GeocodeSearchResult]: A list of `GeocodeSearchResult` objects. Each object in the list
        represents a possible geocoded location, containing both the `latlng` (latitude and
        longitude) and the `address` (a standardized, human-readable format of the location). A list
        is returned because a single input query might correspond to multiple real-world locations
        (e.g., "Springfield" exists in many states). If no location can be found for the given
        input, an empty list will be returned.
    """
    return await geocode_location(location)

  return agent


get_location_resolver_agent: Callable[[], LocationResolverAgent] = lazy_object_proxy.Proxy(
  _get_location_resolver_agent
)
