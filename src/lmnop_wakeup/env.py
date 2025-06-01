import os
from enum import StrEnum
from typing import NewType

from .core.typing import assert_not_none

ApiKey = NewType("ApiKey", str)
"""Represents an API key."""


class EnvName(StrEnum):
  """Represents the names of required environment variables."""

  LANGFUSE_HOST = "LANGFUSE_HOST"
  """The environment variable name for the Langfuse host."""
  LANGFUSE_PUBLIC_KEY = "LANGFUSE_PUBLIC_KEY"
  """The environment variable name for the Langfuse public key."""
  LANGFUSE_SECRET_KEY = "LANGFUSE_SECRET_KEY"
  """The environment variable name for the Langfuse secret key."""
  LITELLM_API_URL = "LITELLM_API_URL"
  """The base url used for communicating through LiteLLM"""
  LITELLM_API_KEY = "LITELLM_API_KEY"
  """The environment variable name for the LiteLLM API token."""
  GEMINI_API_KEY = "GEMINI_API_KEY"
  """The environment variable name for the Gemini API key."""
  GOOGLE_ROUTES_API_KEY = "GOOGLE_ROUTES_API_KEY"
  """The environment variable name for the Google Routes API key."""
  HASS_API_TOKEN = "HASS_API_TOKEN"
  """The environment variable name for the Home Assistant API token."""
  PIRATE_WEATHER_API_KEY = "PIRATE_WEATHER_API_KEY"
  """The environment variable name for the Pirate Weather API key."""
  POSTGRES_CONNECTION_STRING = "POSTGRES_CONNECTION_STRING"
  """The environment variable name for the Postgres database URL."""
  REDIS_CACHE_URL = "REDIS_CACHE_URL"
  """The environment variable name for the Redis cache URL."""


def get_postgres_connection_string() -> str:
  """
  Retrieves the Postgres database URL from environment variables.

  Returns:
    The Postgres database URL.

  Raises:
    EnvironmentError: If the POSTGRES_CONNECTION_STRING environment variable is not set.
  """
  if EnvName.POSTGRES_CONNECTION_STRING not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.POSTGRES_CONNECTION_STRING} not provided"
    )
  return assert_not_none(os.getenv(EnvName.POSTGRES_CONNECTION_STRING))


def get_litellm_api_key() -> ApiKey:
  """
  Retrieves the Home Assistant API key from environment variables.

  Returns:
    The Home Assistant API key.

  Raises:
    EnvironmentError: If the HASS_API_TOKEN environment variable is not set.
  """
  if EnvName.LITELLM_API_KEY not in os.environ:
    raise EnvironmentError(f"Required environment variable {EnvName.LITELLM_API_KEY} not provided")
  return ApiKey(assert_not_none(os.getenv(EnvName.LITELLM_API_KEY)))


def get_litellm_base_url() -> str:
  """
  Retrieves the LiteLLM base URL from environment variables.

  Returns:
    The LiteLLM base URL.

  Raises:
    EnvironmentError: If the LITELLM_API_URL environment variable is not set.
  """
  if EnvName.LITELLM_API_URL not in os.environ:
    raise EnvironmentError(f"Required environment variable {EnvName.LITELLM_API_URL} not provided")
  return assert_not_none(os.getenv(EnvName.LITELLM_API_URL))


def get_hass_api_key() -> ApiKey:
  """
  Retrieves the Home Assistant API key from environment variables.

  Returns:
    The Home Assistant API key.

  Raises:
    EnvironmentError: If the HASS_API_TOKEN environment variable is not set.
  """
  if EnvName.HASS_API_TOKEN not in os.environ:
    raise EnvironmentError(f"Required environment variable {EnvName.HASS_API_TOKEN} not provided")
  return ApiKey(assert_not_none(os.getenv(EnvName.HASS_API_TOKEN)))


def get_pirate_weather_api_key() -> ApiKey:
  """
  Retrieves the Pirate Weather API key from environment variables.

  Returns:
    The Pirate Weather API key.

  Raises:
    EnvironmentError: If the PIRATE_WEATHER_API_KEY environment variable is not set.
  """
  if EnvName.PIRATE_WEATHER_API_KEY not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.PIRATE_WEATHER_API_KEY} not provided"
    )
  return ApiKey(assert_not_none(os.getenv(EnvName.PIRATE_WEATHER_API_KEY)))


def get_google_cloud_api_key() -> ApiKey:
  """
  Retrieves the Google Routes API key from environment variables.

  Returns:
    The Google Routes API key.

  Raises:
    EnvironmentError: If the GOOGLE_ROUTES_API_KEY environment variable is not set.
  """
  if EnvName.GOOGLE_ROUTES_API_KEY not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.GOOGLE_ROUTES_API_KEY} not provided"
    )
  return ApiKey(assert_not_none(os.getenv(EnvName.GOOGLE_ROUTES_API_KEY)))


def get_redis_cache_url() -> str:
  """
  Retrieves the Redis cache URL from environment variables.

  Returns:
    The Redis cache URL.

  Raises:
    EnvironmentError: If the REDIS_CACHE_URL environment variable is not set.
  """
  if EnvName.REDIS_CACHE_URL not in os.environ:
    raise EnvironmentError(f"Required environment variable {EnvName.REDIS_CACHE_URL} not provided")
  return assert_not_none(os.getenv(EnvName.REDIS_CACHE_URL))


def assert_env():
  """
  Asserts that all required environment variables are set.

  Raises:
    EnvironmentError: If any required environment variable is not set.
  """
  for name in list(EnvName):
    if name not in os.environ:
      raise EnvironmentError(f"Required environment variable {name} not provided")
