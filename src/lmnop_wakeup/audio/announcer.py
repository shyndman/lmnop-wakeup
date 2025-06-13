import asyncio
import time

import structlog

from .session import MusicAssistantConnectionError, MusicAssistantSession

logger = structlog.get_logger(__name__)


class BriefingAnnouncerError(Exception):
  """Base exception for BriefingAnnouncer errors."""

  pass


class PlayerNotFoundError(BriefingAnnouncerError):
  """Raised when the configured player is not found or unavailable."""

  pass


class AnnouncementFailedError(BriefingAnnouncerError):
  """Raised when the announcement fails to play."""

  pass


class BriefingAnnouncer:
  """Music Assistant client for playing briefing announcements."""

  def __init__(self, music_assistant_url: str, player_id: str):
    """Initialize the announcer with Music Assistant connection details.

    Args:
        music_assistant_url: URL of the Music Assistant server
        player_id: ID of the player to announce on
    """
    self.music_assistant_url = music_assistant_url
    self.player_id = player_id

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
      async with MusicAssistantSession(self.music_assistant_url) as client:
        await self._validate_player(client)
        await self._play_announcement(client, briefing_url)
        return True
    except MusicAssistantConnectionError:
      raise
    except Exception as e:
      if isinstance(e, BriefingAnnouncerError):
        raise
      logger.exception(f"Unexpected error during announcement: {e}")
      raise AnnouncementFailedError(f"Unexpected error: {str(e)}") from e

  async def _validate_player(self, client) -> None:
    """Validate that the configured player exists and is available."""
    try:
      player = client.players.get(self.player_id)
      if not player:
        raise PlayerNotFoundError(f"Player '{self.player_id}' not found")

      if not player.available:
        raise PlayerNotFoundError(f"Player '{player.name}' is not available")

      logger.info(f"Player '{player.name}' is available for announcements")

    except Exception as e:
      if isinstance(e, PlayerNotFoundError):
        raise
      raise PlayerNotFoundError(f"Error validating player '{self.player_id}': {str(e)}") from e

  async def _play_announcement(self, client, briefing_url: str) -> None:
    """Play the announcement and wait for completion."""
    try:
      logger.info(f"Playing announcement: {briefing_url}")

      # Start the announcement
      await client.players.play_announcement(player_id=self.player_id, url=briefing_url)

      # Wait for announcement to complete (simple polling approach for MVP)
      await self._wait_for_announcement_completion(client)

      logger.info("Announcement completed successfully")

    except Exception as e:
      raise AnnouncementFailedError(f"Failed to play announcement: {str(e)}") from e

  async def _wait_for_announcement_completion(self, client, timeout: float = 300.0) -> None:
    """Wait for the announcement to complete using simple polling.

    Args:
        client: The Music Assistant client
        timeout: Maximum time to wait in seconds (default 5 minutes)
    """
    start_time = time.time()
    check_interval = 1.0  # Check every second

    while time.time() - start_time < timeout:
      try:
        player = client.players.get(self.player_id)
        if not player or not player.announcement_in_progress:
          return  # Announcement completed

        await asyncio.sleep(check_interval)

      except Exception as e:
        logger.warning(f"Error checking announcement status: {e}")
        await asyncio.sleep(check_interval)

    raise AnnouncementFailedError(f"Announcement did not complete within {timeout} seconds")
