from typing import override

import rich
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel

from ..core.tracing import trace
from ..core.typing import ensure
from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName, extract_pydantic_ai_callback
from .geocode_api import GeocodeSearchResult, geocode_location
from .model import NamedLocation, ResolvedLocation


class LocationResolverInput(LangfuseAgentInput):
  """Input for the location resolver agent."""

  home_location: NamedLocation
  """The user's home location, where they begin their day"""
  named_locations: list[NamedLocation]
  """Special locations for the user, that are referenced by shorter titles"""
  address: str
  """The location to resolve."""
  # location: CoordinateLocation | None = None

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "event_location": ensure(self.address),
      "home_location": self.home_location.model_dump_json(),
      "named_locations": "\n".join([f" * {location.name}" for location in self.named_locations])
      + "\n",
    }


class LocationResolverOutput(BaseModel):
  """Output for the location resolver agent."""

  special_location: str | None = None
  """Set to the location's name if the input location was identified as one of the user's named
  locations."""

  geocoded_location: ResolvedLocation | None = None
  """Set to a resolved location object if a likely location candidate was successfully
  determined."""

  failure_reason: str | None = None
  """If no location could be determined, set this value to a ResolutionFailure instance, describing
  the problem. Otherwise leave unset."""


type LocationResolverAgent = LangfuseAgent[LocationResolverInput, LocationResolverOutput]


def _get_location_resolver_agent(config: RunnableConfig) -> LocationResolverAgent:
  """Get the location resolver agent."""
  rich.print(config)
  agent = LangfuseAgent[LocationResolverInput, LocationResolverOutput].create(
    "location_resolver",
    model_name=ModelName.GEMINI_20_FLASH,
    input_type=LocationResolverInput,
    output_type=LocationResolverOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  @trace(name="tool: geocode")
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
        represents a possible geocoded location, containing the `latlng` (latitude and longitude),
        the `address` (a standardized, human-readable format of the location), and
        `distance_from_home_km` (the distance in kilometers from your home location). A list is
        returned because a single input query might correspond to multiple real-world locations
        (e.g., "Springfield" exists in many states). Results are typically ordered by relevance, but
        the distance field can help select the most appropriate option. If no location can be found
        for the given input, an empty list will be returned.
    """
    logger.debug("Geocoding location: {}", location)
    result = await geocode_location(location)
    logger.debug("Geocoding result: {}", result)
    return result

  return agent


_location_resolver_agent: LocationResolverAgent | None = None


def get_location_resolver_agent(config: RunnableConfig) -> LocationResolverAgent:
  global _location_resolver_agent
  if _location_resolver_agent is None:
    _location_resolver_agent = _get_location_resolver_agent(config)
  """Get the location resolver agent."""
  return _location_resolver_agent
