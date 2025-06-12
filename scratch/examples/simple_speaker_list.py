#!/usr/bin/env python3
"""
Simple script to list Music Assistant speakers using the same pattern as BriefingAnnouncer.

This follows the exact same connection pattern as the existing BriefingAnnouncer class
but focuses on listing available speakers instead of playing announcements.

Usage:
    # Ensure MUSIC_ASSISTANT_URL is set in environment
    opr python examples/simple_speaker_list.py
"""

import asyncio
import sys
from pathlib import Path

import aiohttp
import structlog
from music_assistant_client.client import MusicAssistantClient

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lmnop_wakeup.env import get_music_assistant_url

logger = structlog.get_logger(__name__)


class SpeakerEnumerator:
  """Simple Music Assistant client for listing speakers/players."""

  def __init__(self, music_assistant_url: str):
    """Initialize with Music Assistant connection details."""
    self.music_assistant_url = music_assistant_url
    self.client: MusicAssistantClient | None = None
    self.session: aiohttp.ClientSession | None = None

  async def list_speakers(self) -> list[dict]:
    """List all available speakers/players.

    Returns:
        List of speaker info dictionaries
    """
    try:
      await self._ensure_connected()
      return await self._get_all_speakers()
    finally:
      await self._cleanup()

  async def _ensure_connected(self) -> None:
    """Ensure we have a valid connection to Music Assistant."""
    if self.client is not None:
      return

    logger.info(f"Connecting to Music Assistant at {self.music_assistant_url}")
    self.session = aiohttp.ClientSession()
    self.client = MusicAssistantClient(self.music_assistant_url, self.session)

    # Connect with timeout (same as BriefingAnnouncer)
    await asyncio.wait_for(self.client.connect(), timeout=10.0)

    # Start listening for events with init ready signal
    init_ready = asyncio.Event()
    self.listen_task = asyncio.create_task(self.client.start_listening(init_ready))
    await asyncio.wait_for(init_ready.wait(), timeout=15.0)

    logger.info("Successfully connected to Music Assistant")

  async def _get_all_speakers(self) -> list[dict]:
    """Get information about all speakers/players."""
    if not self.client:
      raise RuntimeError("Not connected to Music Assistant")

    speakers = []

    # Based on the BriefingAnnouncer code, we know:
    # - self.client.players.get(player_id) works to get a specific player
    # - players have .available, .name properties

    # Let's try to access the players collection
    if hasattr(self.client, "players"):
      players_manager = self.client.players

      # Try different ways to get all players
      if hasattr(players_manager, "all"):
        # If there's an 'all' property/method
        all_players = players_manager.all
        if callable(all_players):
          all_players = all_players()
          if asyncio.iscoroutine(all_players):
            all_players = await all_players

        logger.info(f"Found {len(all_players)} players via 'all' property")

        for player_id, player in all_players.items():
          speaker_info = self._extract_player_info(player_id, player)
          speakers.append(speaker_info)

      elif hasattr(players_manager, "values"):
        # If it's a dict-like object
        all_players = players_manager.values()
        if callable(all_players):
          all_players = all_players()
          if asyncio.iscoroutine(all_players):
            all_players = await all_players

        logger.info("Found players via 'values' method")

        for player in all_players:
          player_id = getattr(player, "player_id", "unknown")
          speaker_info = self._extract_player_info(player_id, player)
          speakers.append(speaker_info)

      else:
        # Try to explore what's available
        logger.info(f"Players manager type: {type(players_manager)}")
        logger.info(
          f"Available methods: {[m for m in dir(players_manager) if not m.startswith('_')]}"
        )

        # Try some common patterns
        for attr_name in ["items", "get_all", "list", "__iter__"]:
          if hasattr(players_manager, attr_name):
            logger.info(f"Trying {attr_name}...")
            try:
              attr = getattr(players_manager, attr_name)
              if callable(attr):
                result = attr()
                if asyncio.iscoroutine(result):
                  result = await result
                logger.info(f"{attr_name}() returned {type(result)}")
                # Handle the result based on its type
                if hasattr(result, "items"):
                  for player_id, player in result.items():
                    speaker_info = self._extract_player_info(player_id, player)
                    speakers.append(speaker_info)
                  break
                elif hasattr(result, "__iter__"):
                  for item in result:
                    if hasattr(item, "player_id"):
                      speaker_info = self._extract_player_info(item.player_id, item)
                      speakers.append(speaker_info)
                  break
            except Exception as e:
              logger.warning(f"Error trying {attr_name}: {e}")

    return speakers

  def _extract_player_info(self, player_id: str, player) -> dict:
    """Extract relevant information from a player object."""
    try:
      return {
        "id": player_id,
        "name": getattr(player, "name", "Unknown"),
        "available": getattr(player, "available", False),
        "type": getattr(player, "type", "Unknown"),
        "provider": getattr(player, "provider", "Unknown"),
        "state": getattr(player, "state", "Unknown"),
        "volume_level": getattr(player, "volume_level", None),
        "announcement_in_progress": getattr(player, "announcement_in_progress", False),
      }
    except Exception as e:
      logger.warning(f"Error extracting player info for {player_id}: {e}")
      return {
        "id": player_id,
        "name": "Error getting details",
        "available": False,
        "type": "Unknown",
        "provider": "Unknown",
        "state": "Unknown",
        "volume_level": None,
        "announcement_in_progress": False,
      }

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


async def main():
  """Main entry point."""
  try:
    music_assistant_url = get_music_assistant_url()
  except EnvironmentError as e:
    print(f"❌ Configuration error: {e}")
    print("Please ensure MUSIC_ASSISTANT_URL environment variable is set")
    return

  print(f"🔍 Connecting to Music Assistant at {music_assistant_url}")

  enumerator = SpeakerEnumerator(music_assistant_url)

  try:
    speakers = await enumerator.list_speakers()

    if not speakers:
      print("❌ No speakers found")
      return

    print(f"\n🔊 Found {len(speakers)} Music Assistant speakers:")
    print("=" * 80)
    print(f"{'ID':<25} {'Name':<30} {'Available':<10} {'Type':<15}")
    print("-" * 80)

    available_count = 0
    for speaker in speakers:
      status = "✅ Yes" if speaker["available"] else "❌ No"
      print(f"{speaker['id']:<25} {speaker['name']:<30} {status:<10} {speaker['type']:<15}")

      if speaker["available"]:
        available_count += 1
        print(f"  └─ Provider: {speaker['provider']}")
        if speaker["volume_level"] is not None:
          print(f"  └─ Volume: {speaker['volume_level']}%")
        print(f"  └─ State: {speaker['state']}")

    print("-" * 80)
    print(f"Total: {len(speakers)} speakers ({available_count} available)")

    if available_count > 0:
      print("\n✅ Available speakers for announcements:")
      for speaker in speakers:
        if speaker["available"]:
          print(f"  • {speaker['name']} (ID: {speaker['id']})")
    else:
      print("\n⚠️  No speakers are currently available for announcements")

  except Exception as e:
    logger.exception(f"Failed to list speakers: {e}")
    print(f"❌ Error: {e}")


if __name__ == "__main__":
  # Configure basic logging
  structlog.configure(
    processors=[
      structlog.stdlib.filter_by_level,
      structlog.stdlib.add_log_level,
      structlog.processors.TimeStamper(fmt="%H:%M:%S"),
      structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
  )

  asyncio.run(main())
