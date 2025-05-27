from collections.abc import Callable
from typing import override

import lazy_object_proxy
from pydantic import BaseModel

from lmnop_wakeup.core.typing import nn

from ..llm import LangfuseAgent, LangfuseInput, ModelName
from .model import AddressLocation, CoordinateLocation, NamedLocation


class LocationResolverInput(LangfuseInput):
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
      "location": nn(self.location.address),
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
  async def geocode(location: str) -> CoordinateLocation | None:
    """Geocode a location string, like an address or the name of a place, to geographic coordinates.
    This agent is designed to take a natural language location query and convert it into a precise
    latitude and longitude.

    Args:
      location (str): The location string to geocode. This can be:
        - A full address (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
        - A partial address (e.g., "Eiffel Tower, Paris")
        - A named place (e.g., "Central Park", "Golden Gate Bridge")
        - A city and country (e.g., "London, UK")

    Returns:
      CoordinateLocation | None: A `CoordinateLocation` object containing the latitude and longitude
        if the location is successfully geocoded, otherwise `None`.
    """
    # TODO: Write me
    return CoordinateLocation(latlng=(43.69349321829292, -79.29817931845875))

  return agent


get_location_resolver_agent: Callable[[], LocationResolverAgent] = lazy_object_proxy.Proxy(
  _get_location_resolver_agent
)
