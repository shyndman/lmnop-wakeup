"""CLI commands for audio production and announcements."""

import asyncio
from datetime import date
from typing import override

import structlog
import uvicorn
from clypi import Command, arg
from rich.console import Console
from rich.table import Table

from ..core.terminal import file_hyperlink
from ..env import assert_env
from ..paths import BriefingDirectory

logger = structlog.get_logger()


class AudioProduction(Command):
  """Add audio production to an existing briefing"""

  briefing_date: date = arg(inherited=True)

  @override
  async def run(self):
    from ..audio.production import AudioProductionMixer

    assert_env()

    briefing_dir = BriefingDirectory.for_date(self.briefing_date)

    if not briefing_dir.exists():
      print(f"No briefing directory found for {self.briefing_date}")
      return

    if not briefing_dir.briefing_audio_path.exists():
      print(f"No briefing audio found at {file_hyperlink(briefing_dir.briefing_audio_path)}")
      return

    # Load the consolidated script for timing
    try:
      consolidated_script_path = briefing_dir.consolidated_brief_json_path
      if consolidated_script_path.exists():
        from ..brief.model import ConsolidatedBriefingScript

        script_content = consolidated_script_path.read_text()
        script = ConsolidatedBriefingScript.model_validate_json(script_content)
      else:
        # Fallback to regular script and consolidate it
        script = briefing_dir.load_script()
        script = script.consolidate_dialogue()
    except Exception as e:
      print(f"Error loading briefing script: {e}")
      return

    # Mix audio production with briefing
    mixer = AudioProductionMixer()

    try:
      output_path = mixer.mix_audio_with_briefing(
        briefing_audio_path=briefing_dir.briefing_audio_path,
        script=script,
        audio_files_dir=briefing_dir.base_path,
        output_path=briefing_dir.master_audio_path,
      )
      print(f"Audio production completed successfully: {file_hyperlink(output_path)}")
      print(f"Briefing directory: {file_hyperlink(briefing_dir.base_path)}")
    except Exception as e:
      print(f"Error in audio production: {e}")


class ListPlayers(Command):
  """List Music Assistant players"""

  @override
  async def run(self):
    from ..audio.session import MusicAssistantSession
    from ..env import get_music_assistant_url

    console = Console()

    try:
      music_assistant_url = get_music_assistant_url()
    except EnvironmentError as e:
      console.print(f"[red]Configuration error:[/red] {e}")
      console.print("Please ensure MUSIC_ASSISTANT_URL environment variable is set")
      return

    console.print(f"🔍 Connecting to Music Assistant at {music_assistant_url}")

    try:
      async with MusicAssistantSession(music_assistant_url) as client:
        # Get all players from the players collection
        all_players = list(client.players)

        if not all_players:
          console.print("[red]No players found[/red]")
          return

        table = Table(title=f"Music Assistant Players ({len(all_players)} found)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Available", justify="center")
        table.add_column("Type", style="green")
        table.add_column("Details", style="dim")

        available_count = 0
        available_players = []

        for player in all_players:
          player_id = player.player_id
          status = "✅" if player.available else "❌"
          player_type = getattr(player, "type", "Unknown")

          details_parts = []
          provider = getattr(player, "provider", "Unknown")
          details_parts.append(f"Provider: {provider}")

          volume_level = getattr(player, "volume_level", None)
          if volume_level is not None:
            details_parts.append(f"Volume: {volume_level}%")

          state = getattr(player, "state", "Unknown")
          details_parts.append(f"State: {state}")

          details = "\n".join(details_parts)

          table.add_row(player_id, player.name, status, player_type, details)

          if player.available:
            available_count += 1
            available_players.append((player_id, player.name))

        console.print(table)
        console.print(
          f"\n[bold]Summary:[/bold] {available_count} of {len(all_players)} players available"
        )

        if available_players:
          console.print("\n[green]Available for announcements:[/green]")
          for player_id, player_name in available_players:
            console.print(f"  • {player_name} [dim]({player_id})[/dim]")
        else:
          console.print(
            "\n[yellow]⚠️  No players are currently available for announcements[/yellow]"
          )

    except Exception as e:
      logger.exception(f"Failed to list players: {e}")
      console.print(f"[red]Error:[/red] {e}")


class Announce(Command):
  """Announce briefing via Music Assistant"""

  briefing_date: date = arg(inherited=True)
  player_id: str | None = arg(
    default=None, help="Music Assistant player ID (overrides environment default)"
  )

  @override
  async def run(self):
    from ..audio.announcer import (
      AnnouncementFailedError,
      BriefingAnnouncer,
      MusicAssistantConnectionError,
      PlayerNotFoundError,
    )
    from ..env import (
      get_music_assistant_player_id,
      get_music_assistant_url,
      get_wakeup_server_base_url,
    )
    from ..server import app

    console = Console()

    # Check if briefing audio exists
    briefing_dir = BriefingDirectory.for_date(self.briefing_date)
    if not briefing_dir.has_master_audio():
      console.print(f"[red]Error:[/red] No audio file found for {self.briefing_date}")
      console.print(f"Expected audio at: {file_hyperlink(briefing_dir.master_audio_path)}")
      console.print("Generate the briefing first using the main workflow.")
      return

    # Get configuration
    try:
      music_assistant_url = get_music_assistant_url()
      server_base_url = get_wakeup_server_base_url()
      player_id = self.player_id or get_music_assistant_player_id()
    except EnvironmentError as e:
      console.print(f"[red]Configuration error:[/red] {e}")
      console.print("Required environment variables:")
      console.print("  • MUSIC_ASSISTANT_URL")
      console.print("  • WAKEUP_SERVER_BASE_URL")
      console.print("  • MUSIC_ASSISTANT_PLAYER_ID (or use --player-id)")
      return

    # Construct briefing URL
    briefing_url = f"{server_base_url}/briefing/{self.briefing_date}/audio"

    console.print(f"🎵 Announcing briefing for {self.briefing_date}")
    console.print(f"Player: {player_id}")
    console.print(f"Audio URL: {briefing_url}")

    # Start temporary server for the announcement
    console.print("🚀 Starting temporary server...")

    # Create server config
    config = uvicorn.Config(
      app=app,
      host="0.0.0.0",
      port=8002,
      log_config=None,
      log_level="error",  # Minimize server output
    )
    server = uvicorn.Server(config)

    try:
      # Start server in background
      server_task = asyncio.create_task(server.serve())

      # Give server a moment to start
      await asyncio.sleep(2.0)
      console.print("✅ Server started")

      # Make the announcement
      announcer = BriefingAnnouncer(music_assistant_url, player_id)
      await announcer.announce(briefing_url)
      console.print("[green]✅ Briefing announced successfully![/green]")

    except MusicAssistantConnectionError as e:
      console.print(f"[red]Connection error:[/red] {e}")
      console.print(f"Failed to connect to Music Assistant at {music_assistant_url}")

    except PlayerNotFoundError as e:
      console.print(f"[red]Player error:[/red] {e}")
      console.print(f"Player '{player_id}' not found or unavailable")
      console.print("Use 'opr wakeup list-players' to see available players")

    except AnnouncementFailedError as e:
      console.print(f"[red]Announcement failed:[/red] {e}")

    except Exception as e:
      logger.exception(f"Unexpected error during announcement: {e}")
      console.print(f"[red]Unexpected error:[/red] {e}")

    finally:
      # Always shut down the server
      console.print("🛑 Shutting down server...")
      server.should_exit = True
      server_task.cancel()  # type: ignore
      try:
        await server_task  # type: ignore
      except asyncio.CancelledError:
        pass
      console.print("✅ Server stopped")
