import asyncio
import time

import aiohttp
import structlog
from music_assistant_client.client import MusicAssistantClient

logger = structlog.get_logger(__name__)


class BriefingAnnouncerError(Exception):
  """Base exception for BriefingAnnouncer errors."""

  pass


class MusicAssistantConnectionError(BriefingAnnouncerError):
  """Raised when unable to connect to Music Assistant."""

  pass


class PlayerNotFoundError(BriefingAnnouncerError):
  """Raised when the configured player is not found or unavailable."""

  pass


class AnnouncementFailedError(BriefingAnnouncerError):
  """Raised when the announcement fails to play."""

  pass


class BriefingAnnouncer:
  """MVP Music Assistant client for playing briefing announcements."""

  def __init__(self, music_assistant_url: str, player_id: str):
    """Initialize the announcer with Music Assistant connection details.

    Args:
        music_assistant_url: URL of the Music Assistant server
        player_id: ID of the player to announce on
    """
    self.music_assistant_url = music_assistant_url
    self.player_id = player_id
    self.client: MusicAssistantClient | None = None
    self.session: aiohttp.ClientSession | None = None

  async def announce(self, briefing_url: str) -> bool:
    """Play an announcement on the configured player.

    Args:
        briefing_url: HTTP URL of the audio file to play

    Returns:
        True if announcement completed successfully

    Raises:
        MusicAssistantConnectionError: If unable to connect to Music Assistant
        PlayerNotFoundError: If player is not found or unavailable
        AnnouncementFailedError: If announcement fails to play
    """
    try:
      await self._ensure_connected()
      await self._validate_player()
      await self._play_announcement(briefing_url)
      return True
    except Exception as e:
      if isinstance(e, BriefingAnnouncerError):
        raise
      logger.exception(f"Unexpected error during announcement: {e}")
      raise AnnouncementFailedError(f"Unexpected error: {str(e)}") from e
    finally:
      await self._cleanup()

  async def _ensure_connected(self) -> None:
    """Ensure we have a valid connection to Music Assistant."""
    if self.client is not None:
      return

    try:
      logger.info(f"Connecting to Music Assistant at {self.music_assistant_url}")
      self.session = aiohttp.ClientSession()
      self.client = MusicAssistantClient(self.music_assistant_url, self.session)

      # Connect with timeout
      await asyncio.wait_for(self.client.connect(), timeout=10.0)

      # Start listening for events with init ready signal
      init_ready = asyncio.Event()
      self.listen_task = asyncio.create_task(self.client.start_listening(init_ready))
      await asyncio.wait_for(init_ready.wait(), timeout=15.0)

      logger.info("Successfully connected to Music Assistant")

    except asyncio.TimeoutError as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Connection timeout to Music Assistant at {self.music_assistant_url}"
      ) from e
    except aiohttp.ClientConnectorError as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Connection refused to Music Assistant at {self.music_assistant_url}: {str(e)}"
      ) from e
    except Exception as e:
      await self._cleanup()
      raise MusicAssistantConnectionError(
        f"Failed to connect to Music Assistant at {self.music_assistant_url}: {str(e)}"
      ) from e

  async def _validate_player(self) -> None:
    """Validate that the configured player exists and is available."""
    if not self.client:
      raise MusicAssistantConnectionError("Not connected to Music Assistant")

    try:
      player = self.client.players.get(self.player_id)
      if not player:
        raise PlayerNotFoundError(f"Player '{self.player_id}' not found")

      if not player.available:
        raise PlayerNotFoundError(f"Player '{player.name}' is not available")

      logger.info(f"Player '{player.name}' is available for announcements")

    except Exception as e:
      if isinstance(e, PlayerNotFoundError):
        raise
      raise PlayerNotFoundError(f"Error validating player '{self.player_id}': {str(e)}") from e

  async def _play_announcement(self, briefing_url: str) -> None:
    """Play the announcement and wait for completion."""
    if not self.client:
      raise MusicAssistantConnectionError("Not connected to Music Assistant")

    try:
      logger.info(f"Playing announcement: {briefing_url}")

      # Start the announcement
      await self.client.players.play_announcement(player_id=self.player_id, url=briefing_url)

      # Wait for announcement to complete (simple polling approach for MVP)
      await self._wait_for_announcement_completion()

      logger.info("Announcement completed successfully")

    except Exception as e:
      raise AnnouncementFailedError(f"Failed to play announcement: {str(e)}") from e

  async def _wait_for_announcement_completion(self, timeout: float = 300.0) -> None:
    """Wait for the announcement to complete using simple polling.

    Args:
        timeout: Maximum time to wait in seconds (default 5 minutes)
    """
    start_time = time.time()
    check_interval = 1.0  # Check every second

    while time.time() - start_time < timeout:
      try:
        if self.client is not None:
          player = self.client.players.get(self.player_id)
        else:
          raise MusicAssistantConnectionError("Client is None")
        if not player or not player.announcement_in_progress:
          return  # Announcement completed

        await asyncio.sleep(check_interval)

      except Exception as e:
        logger.warning(f"Error checking announcement status: {e}")
        await asyncio.sleep(check_interval)

    raise AnnouncementFailedError(f"Announcement did not complete within {timeout} seconds")

  async def _cleanup(self) -> None:
    """Clean up connections and resources."""
    if hasattr(self, "listen_task") and self.listen_task:
      self.listen_task.cancel()
      try:
        await self.listen_task
      except asyncio.CancelledError:
        pass

    if self.client:
      try:
        await self.client.disconnect()
      except Exception as e:
        logger.debug(f"Error disconnecting client: {e}")
      self.client = None

    if self.session:
      try:
        await self.session.close()
      except Exception as e:
        logger.debug(f"Error closing session: {e}")
      self.session = None
