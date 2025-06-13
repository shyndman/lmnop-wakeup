import asyncio

import aiohttp
import structlog
from music_assistant_client.client import MusicAssistantClient

logger = structlog.get_logger(__name__)


class MusicAssistantConnectionError(Exception):
  """Raised when unable to connect to Music Assistant."""

  pass


class MusicAssistantSession:
  """Manages Music Assistant connection lifecycle and provides access to the client."""

  def __init__(self, url: str):
    """Initialize with Music Assistant server URL."""
    self._url = url
    self._client: MusicAssistantClient | None = None
    self._session: aiohttp.ClientSession | None = None
    self._listen_task: asyncio.Task | None = None

  async def __aenter__(self) -> MusicAssistantClient:
    """Connect to Music Assistant and return the client."""
    await self._ensure_connected()
    if not self._client:
      raise MusicAssistantConnectionError("Failed to establish connection")
    return self._client

  async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Clean up connections and resources."""
    await self._cleanup()

  async def _ensure_connected(self) -> None:
    """Ensure we have a valid connection to Music Assistant."""
    if self._client is not None:
      return

    try:
      logger.info(f"Connecting to Music Assistant at {self._url}")
      self._session = aiohttp.ClientSession()
      self._client = MusicAssistantClient(self._url, self._session)

      # Connect with timeout
      await asyncio.wait_for(self._client.connect(), timeout=10.0)

      # Start listening for events with init ready signal
      init_ready = asyncio.Event()
      self._listen_task = asyncio.create_task(self._client.start_listening(init_ready))
      await asyncio.wait_for(init_ready.wait(), timeout=15.0)

      logger.info("Successfully connected to Music Assistant")

    except asyncio.TimeoutError as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Connection timeout to Music Assistant at {self._url}"
      ) from e
    except aiohttp.ClientConnectorError as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Connection refused to Music Assistant at {self._url}: {str(e)}"
      ) from e
    except Exception as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Failed to connect to Music Assistant at {self._url}: {str(e)}"
      ) from e

  async def _cleanup(self) -> None:
    """Clean up connections and resources."""
    if self._listen_task:
      self._listen_task.cancel()
      try:
        await self._listen_task
      except asyncio.CancelledError:
        pass
      self._listen_task = None

    if self._client:
      try:
        await self._client.disconnect()
      except Exception as e:
        logger.debug(f"Error disconnecting client: {e}")
      self._client = None

    if self._session:
      try:
        await self._session.close()
      except Exception as e:
        logger.debug(f"Error closing session: {e}")
      self._session = None
