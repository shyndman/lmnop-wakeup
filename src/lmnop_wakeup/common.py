import os
from enum import StrEnum
from typing import NewType

from .utils.typing import assert_not_none

ApiKey = NewType("ApiKey", str)
"""Represents an API key."""


def api_key_parser(raw: str | list[str]) -> ApiKey:
  """
  Parses a raw string or list of strings into an ApiKey.

  Args:
    raw: The raw input string or list of strings.

  Returns:
    An ApiKey instance.

  Raises:
    ValueError: If the input is a list or an empty string.
  """
  if isinstance(raw, list):
    raise ValueError("List input not supported")
  if len(raw.strip()) == 0:
    raise ValueError("API key may not be empty")
  return ApiKey(raw)


class EnvName(StrEnum):
  """Represents the names of required environment variables."""

  LITELLM_API_KEY = "LITELLM_API_KEY"
  """The environment variable name for the LiteLLM API token."""
  GEMINI_API_KEY = "GEMINI_API_KEY"
  """The environment variable name for the Gemini API key."""
  HASS_API_TOKEN = "HASS_API_TOKEN"
  """The environment variable name for the Home Assistant API token."""
  PIRATE_WEATHER_API_KEY = "PIRATE_WEATHER_API_KEY"
  """The environment variable name for the Pirate Weather API key."""
  GOOGLE_ROUTES_API_KEY = "GOOGLE_ROUTES_API_KEY"
  """The environment variable name for the Google Routes API key."""
  LANGFUSE_PUBLIC_KEY = "LANGFUSE_PUBLIC_KEY"
  """The environment variable name for the Langfuse public key."""
  LANGFUSE_SECRET_KEY = "LANGFUSE_SECRET_KEY"
  """The environment variable name for the Langfuse secret key."""
  LANGFUSE_HOST = "LANGFUSE_HOST"
  """The environment variable name for the Langfuse host."""


def get_litellm_api_key() -> ApiKey:
  """
  Retrieves the Home Assistant API key from environment variables.

  Returns:
    The Home Assistant API key.

  Raises:
    EnvironmentError: If the HASS_API_TOKEN environment variable is not set.
  """
  return ApiKey(assert_not_none(os.getenv(EnvName.LITELLM_API_KEY)))


def get_hass_api_key() -> ApiKey:
  """
  Retrieves the Home Assistant API key from environment variables.

  Returns:
    The Home Assistant API key.

  Raises:
    EnvironmentError: If the HASS_API_TOKEN environment variable is not set.
  """
  return ApiKey(assert_not_none(os.getenv(EnvName.HASS_API_TOKEN)))


def get_pirate_weather_api_key() -> ApiKey:
  """
  Retrieves the Pirate Weather API key from environment variables.

  Returns:
    The Pirate Weather API key.

  Raises:
    EnvironmentError: If the PIRATE_WEATHER_API_KEY environment variable is not set.
  """
  return ApiKey(assert_not_none(os.getenv(EnvName.PIRATE_WEATHER_API_KEY)))


def get_google_routes_api_key() -> ApiKey:
  """
  Retrieves the Google Routes API key from environment variables.

  Returns:
    The Google Routes API key.

  Raises:
    EnvironmentError: If the GOOGLE_ROUTES_API_KEY environment variable is not set.
  """
  return ApiKey(assert_not_none(os.getenv(EnvName.GOOGLE_ROUTES_API_KEY)))


def assert_env():
  """
  Asserts that all required environment variables are set.

  Raises:
    EnvironmentError: If any required environment variable is not set.
  """
  for name in list(EnvName):
    if name not in os.environ:
      raise EnvironmentError(f"Required environment variable {name} not provided")
