#!/usr/bin/env python3
"""
Example script to enumerate Music Assistant speakers/players.

This script demonstrates how to connect to Music Assistant and list all available
speakers/players that can be used for announcements.

Usage:
    # Set environment variables first
    export MUSIC_ASSISTANT_URL="http://your-music-assistant-server:8095"

    # Run the script
    python examples/enumerate_speakers.py
"""

import asyncio
import sys
from pathlib import Path

import aiohttp
import structlog
from music_assistant_client.client import MusicAssistantClient

# Add the src directory to the path so we can import from the project
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lmnop_wakeup.env import get_music_assistant_url

logger = structlog.get_logger(__name__)


async def enumerate_speakers():
  """Enumerate all available Music Assistant speakers/players."""

  # Get Music Assistant URL from environment
  try:
    music_assistant_url = get_music_assistant_url()
  except EnvironmentError as e:
    logger.error(f"Configuration error: {e}")
    logger.info("Please set MUSIC_ASSISTANT_URL environment variable")
    return

  session = None
  client = None

  try:
    logger.info(f"Connecting to Music Assistant at {music_assistant_url}")

    # Create HTTP session and client
    session = aiohttp.ClientSession()
    client = MusicAssistantClient(music_assistant_url, session)

    # Connect with timeout
    await asyncio.wait_for(client.connect(), timeout=10.0)

    # Start listening for events with init ready signal
    init_ready = asyncio.Event()
    listen_task = asyncio.create_task(client.start_listening(init_ready))
    await asyncio.wait_for(init_ready.wait(), timeout=15.0)

    logger.info("Successfully connected to Music Assistant")

    # Get all players
    logger.info("Enumerating all players...")

    # The players attribute should be a collection/manager
    # Based on the announcer code, we can get individual players by ID
    # Let's try to access the players collection directly

    if hasattr(client, "players"):
      players_manager = client.players
      logger.info(f"Players manager type: {type(players_manager)}")

      # Try to get all players - this might be a method or property
      if hasattr(players_manager, "all"):
        all_players = players_manager.all
        logger.info(f"Found {len(all_players)} total players")

        print("\n=== Music Assistant Speakers/Players ===")
        print(f"{'ID':<20} {'Name':<30} {'Available':<10} {'Type':<15}")
        print("-" * 75)

        for player_id, player in all_players.items():
          try:
            available = "Yes" if player.available else "No"
            player_type = getattr(player, "type", "Unknown")
            print(f"{player_id:<20} {player.name:<30} {available:<10} {player_type:<15}")

            # Show additional details for available players
            if player.available:
              print(f"  └─ Provider: {getattr(player, 'provider', 'Unknown')}")
              if hasattr(player, "volume_level"):
                print(f"  └─ Volume: {player.volume_level}%")
              if hasattr(player, "state"):
                print(f"  └─ State: {player.state}")

          except Exception as e:
            logger.warning(f"Error getting details for player {player_id}: {e}")
            print(f"{player_id:<20} {'Error getting details':<30} {'Unknown':<10} {'Unknown':<15}")

        print(f"\nTotal: {len(all_players)} players found")

        # Show available players suitable for announcements
        available_players = [
          (pid, player) for pid, player in all_players.items() if player.available
        ]

        if available_players:
          print(f"\n=== Available Players for Announcements ({len(available_players)}) ===")
          for player_id, player in available_players:
            print(f"  • {player.name} (ID: {player_id})")
        else:
          print("\n⚠️  No players are currently available for announcements")

      elif hasattr(players_manager, "__iter__"):
        # If it's iterable
        logger.info("Players manager is iterable, iterating...")
        print("\n=== Music Assistant Speakers/Players ===")
        for player in players_manager:
          try:
            available = "Yes" if player.available else "No"
            player_type = getattr(player, "type", "Unknown")
            print(f"{player.player_id:<20} {player.name:<30} {available:<10} {player_type:<15}")
          except Exception as e:
            logger.warning(f"Error getting details for player: {e}")

      else:
        # Try to explore the players manager
        logger.info(f"Players manager attributes: {dir(players_manager)}")

        # Try common methods
        for method_name in ["get_all", "items", "values", "keys"]:
          if hasattr(players_manager, method_name):
            logger.info(f"Found method: {method_name}")
            try:
              result = getattr(players_manager, method_name)()
              if asyncio.iscoroutine(result):
                result = await result
              logger.info(f"{method_name}() returned: {type(result)}")
              if hasattr(result, "__len__"):
                logger.info(f"Length: {len(result)}")
            except Exception as e:
              logger.warning(f"Error calling {method_name}(): {e}")

    else:
      logger.error("Client does not have 'players' attribute")
      logger.info(
        f"Client attributes: {[attr for attr in dir(client) if not attr.startswith('_')]}"
      )

    # Cancel the listen task
    if "listen_task" in locals():
      listen_task.cancel()
      try:
        await listen_task
      except asyncio.CancelledError:
        pass

  except asyncio.TimeoutError:
    logger.error(f"Connection timeout to Music Assistant at {music_assistant_url}")
  except aiohttp.ClientConnectorError as e:
    logger.error(f"Connection refused to Music Assistant at {music_assistant_url}: {str(e)}")
  except Exception as e:
    logger.exception(f"Failed to enumerate speakers: {e}")
  finally:
    # Cleanup
    if client:
      try:
        await client.disconnect()
      except Exception as e:
        logger.debug(f"Error disconnecting client: {e}")

    if session:
      try:
        await session.close()
      except Exception as e:
        logger.debug(f"Error closing session: {e}")


async def test_specific_player(player_id: str):
  """Test getting a specific player by ID."""
  try:
    music_assistant_url = get_music_assistant_url()
  except EnvironmentError as e:
    logger.error(f"Configuration error: {e}")
    return

  session = None
  client = None

  try:
    logger.info(f"Testing player ID: {player_id}")

    session = aiohttp.ClientSession()
    client = MusicAssistantClient(music_assistant_url, session)

    await asyncio.wait_for(client.connect(), timeout=10.0)

    init_ready = asyncio.Event()
    listen_task = asyncio.create_task(client.start_listening(init_ready))
    await asyncio.wait_for(init_ready.wait(), timeout=15.0)

    # Test getting specific player (like in the announcer)
    player = client.players.get(player_id)
    if player:
      print(f"\n=== Player Details: {player_id} ===")
      print(f"Name: {player.name}")
      print(f"Available: {player.available}")
      print(f"Type: {getattr(player, 'type', 'Unknown')}")
      print(f"Provider: {getattr(player, 'provider', 'Unknown')}")

      if hasattr(player, "volume_level"):
        print(f"Volume: {player.volume_level}%")
      if hasattr(player, "state"):
        print(f"State: {player.state}")
      if hasattr(player, "announcement_in_progress"):
        print(f"Announcement in progress: {player.announcement_in_progress}")

      # Show all attributes for debugging
      print(f"\nAll attributes: {[attr for attr in dir(player) if not attr.startswith('_')]}")
    else:
      print(f"Player '{player_id}' not found")

    listen_task.cancel()
    try:
      await listen_task
    except asyncio.CancelledError:
      pass

  except Exception as e:
    logger.exception(f"Error testing player {player_id}: {e}")
  finally:
    if client:
      try:
        await client.disconnect()
      except Exception as e:
        logger.debug(f"Error disconnecting: {e}")
    if session:
      try:
        await session.close()
      except Exception as e:
        logger.debug(f"Error closing session: {e}")


async def main():
  """Main entry point."""
  import argparse

  parser = argparse.ArgumentParser(description="Enumerate Music Assistant speakers")
  parser.add_argument("--test-player", help="Test a specific player ID")
  args = parser.parse_args()

  if args.test_player:
    await test_specific_player(args.test_player)
  else:
    await enumerate_speakers()


if __name__ == "__main__":
  # Configure logging
  structlog.configure(
    processors=[
      structlog.stdlib.filter_by_level,
      structlog.stdlib.add_logger_name,
      structlog.stdlib.add_log_level,
      structlog.stdlib.PositionalArgumentsFormatter(),
      structlog.processors.TimeStamper(fmt="iso"),
      structlog.processors.StackInfoRenderer(),
      structlog.processors.format_exc_info,
      structlog.processors.UnicodeDecoder(),
      structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
  )

  asyncio.run(main())
