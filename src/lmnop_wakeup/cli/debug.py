"""Debug commands for testing and development."""

from datetime import datetime, timedelta
from typing import override

import structlog
from clypi import Command
from random_word import RandomWords
from rich.console import Console
from rich.progress import track

from ..core.date import TimeInfo
from ..env import assert_env
from ..events.calendar.gcalendar_api import (
  AUTOMATION_SCHEDULER_CALENDAR_ID,
  upsert_calendar_event,
)
from ..events.model import CalendarEvent

logger = structlog.get_logger()


class AddScheduleEvents(Command):
  """Add test events to the Automation Scheduler calendar."""

  @override
  async def run(self):
    assert_env()
    console = Console()

    # Initialize random word generator
    r = RandomWords()

    # Calculate event times
    now = datetime.now().astimezone()
    first_event_time = now + timedelta(minutes=1)

    console.print("[yellow]Creating 30 test events in Automation Scheduler calendar[/yellow]")
    console.print(f"First event will start at: {first_event_time.strftime('%H:%M:%S')}")

    success_count = 0
    failure_count = 0

    # Create 30 events, 2 minutes apart
    for i in track(range(30), description="Creating events..."):
      # Calculate start time (first event at 1 minute, then every 2 minutes)
      start_time = first_event_time + timedelta(minutes=i * 2)
      end_time = start_time + timedelta(minutes=1)

      # Generate event ID in base32hex format
      event_id = f"st0000{i}"

      # Generate 5 random words for description
      try:
        random_words = [r.get_random_word() for _ in range(5)]
        description = " ".join(random_words)
      except Exception as e:
        logger.warning(f"Failed to generate random words: {e}")
        description = f"Test event {i + 1} - random word generation failed"

      # Create event
      event = CalendarEvent(
        id=event_id,
        summary=f"lmnop:schedule_test({start_time.strftime('%H:%M:%S')})",
        description=description,
        start=TimeInfo(dateTime=start_time),
        end=TimeInfo(dateTime=end_time),
      )

      # Upsert event
      try:
        upsert_calendar_event(AUTOMATION_SCHEDULER_CALENDAR_ID, event)
        success_count += 1
        logger.debug(f"Created event {event_id}")
      except Exception as e:
        failure_count += 1
        logger.error(f"Failed to create event {event_id}: {e}")
        console.print(f"[red]Failed to create event {i + 1}: {e}[/red]")

    # Summary
    console.print()
    console.print(f"[green]Successfully created {success_count} events[/green]")
    if failure_count > 0:
      console.print(f"[red]Failed to create {failure_count} events[/red]")
    console.print(f"Calendar ID: {AUTOMATION_SCHEDULER_CALENDAR_ID}")


class Debug(Command):
  """Debug commands for testing and development."""

  subcommand: AddScheduleEvents
