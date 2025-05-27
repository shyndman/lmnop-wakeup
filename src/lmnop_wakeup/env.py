import os
from enum import StrEnum
from typing import NewType

from .core.typing import assert_not_none

ApiKey = NewType("ApiKey", str)
"""Represents an API key."""


class EnvName(StrEnum):
  """Represents the names of required environment variables."""

  LITELLM_API_URL = "LITELLM_API_URL"
  """The base url used for communicating through LiteLLM"""
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
  POSTGRES_CONNECTION_STRING = "POSTGRES_CONNECTION_STRING"
  """The environment variable name for the Postgres database URL."""


def get_postgres_connection_string() -> str:
  """
  Retrieves the Postgres database URL from environment variables.

  Returns:
    The Postgres database URL.

  Raises:
    EnvironmentError: If the POSTGRES_CONNECTION_STRING environment variable is not set.
  """
  return assert_not_none(os.getenv(EnvName.POSTGRES_CONNECTION_STRING))


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


def get_google_cloud_api_key() -> ApiKey:
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
