import os
from enum import StrEnum
from pathlib import Path
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
  MUSIC_ASSISTANT_URL = "MUSIC_ASSISTANT_URL"
  """The environment variable name for the Music Assistant server URL."""
  MUSIC_ASSISTANT_PLAYER_ID = "MUSIC_ASSISTANT_PLAYER_ID"
  """The environment variable name for the Music Assistant player ID."""
  WAKEUP_SERVER_BASE_URL = "WAKEUP_SERVER_BASE_URL"
  """The environment variable name for the base URL that Music Assistant can reach back to."""
  FINAL_OUT_PATH = "FINAL_OUT_PATH"
  """The environment variable name for the directory where final briefing files are copied."""


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


def get_music_assistant_url() -> str:
  """
  Retrieves the Music Assistant server URL from environment variables.

  Returns:
    The Music Assistant server URL.

  Raises:
    EnvironmentError: If the MUSIC_ASSISTANT_URL environment variable is not set.
  """
  if EnvName.MUSIC_ASSISTANT_URL not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.MUSIC_ASSISTANT_URL} not provided"
    )
  return assert_not_none(os.getenv(EnvName.MUSIC_ASSISTANT_URL))


def get_music_assistant_player_id() -> str:
  """
  Retrieves the Music Assistant player ID from environment variables.

  Returns:
    The Music Assistant player ID.

  Raises:
    EnvironmentError: If the MUSIC_ASSISTANT_PLAYER_ID environment variable is not set.
  """
  if EnvName.MUSIC_ASSISTANT_PLAYER_ID not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.MUSIC_ASSISTANT_PLAYER_ID} not provided"
    )
  return assert_not_none(os.getenv(EnvName.MUSIC_ASSISTANT_PLAYER_ID))


def get_wakeup_server_base_url() -> str:
  """
  Retrieves the wakeup server base URL from environment variables.

  Returns:
    The wakeup server base URL that Music Assistant can reach.

  Raises:
    EnvironmentError: If the WAKEUP_SERVER_BASE_URL environment variable is not set.
  """
  if EnvName.WAKEUP_SERVER_BASE_URL not in os.environ:
    raise EnvironmentError(
      f"Required environment variable {EnvName.WAKEUP_SERVER_BASE_URL} not provided"
    )
  return assert_not_none(os.getenv(EnvName.WAKEUP_SERVER_BASE_URL))


def get_final_out_path() -> Path:
  """
  Retrieves and validates the final output path from environment variables.

  Returns:
    The final output path as a Path object.

  Raises:
    EnvironmentError: If the FINAL_OUT_PATH environment variable is not set or the path is invalid.
  """
  if EnvName.FINAL_OUT_PATH not in os.environ:
    raise EnvironmentError(f"Required environment variable {EnvName.FINAL_OUT_PATH} not provided")

  path_str = assert_not_none(os.getenv(EnvName.FINAL_OUT_PATH))
  final_path = Path(path_str)

  # Create directory if it doesn't exist
  try:
    final_path.mkdir(parents=True, exist_ok=True)
  except (OSError, PermissionError) as e:
    raise EnvironmentError(f"Cannot create or access final output directory {final_path}: {e}")

  # Check if directory is writable
  if not os.access(final_path, os.W_OK):
    raise EnvironmentError(f"Final output directory {final_path} is not writable")

  return final_path


def assert_env():
  """
  Asserts that all required environment variables are set.

  Raises:
    EnvironmentError: If any required environment variable is not set.
  """
  for name in list(EnvName):
    if name == EnvName.FINAL_OUT_PATH:
      continue

    if name not in os.environ:
      raise EnvironmentError(f"Required environment variable {name} not provided")
