"""CLI commands for task management."""

from datetime import date, datetime, timedelta
from typing import override

import structlog
from clypi import Command, arg
from googleapiclient.errors import HttpError
from rich.console import Console
from rich.markdown import Markdown

from ..arg import parse_date_arg
from ..env import assert_env

logger = structlog.get_logger()


class Tasks(Command):
  """View and manage Google Tasks"""

  markdown: bool = arg(default=False, help="display tasks in enhanced markdown format")
  summary: bool = arg(default=False, help="show only summary information (requires --markdown)")
  compact: bool = arg(default=False, help="use compact single-line format (requires --markdown)")
  group_by_status: bool = arg(
    default=False, help="group tasks by status: overdue, due today, etc. (requires --markdown)"
  )
  include_completed: bool = arg(default=False, help="include completed tasks in output")
  start_date: date | None = arg(
    default=None,
    parser=parse_date_arg,
    help="start date for task filtering [format: YYYY-MM-DD | +N | today | tomorrow]",
  )
  end_date: date | None = arg(
    default=None,
    parser=parse_date_arg,
    help="end date for task filtering [format: YYYY-MM-DD | +N | today | tomorrow]",
  )

  @override
  async def run(self):
    console = Console()
    assert_env()

    if self.summary and not self.markdown:
      console.print("[red]Error:[/red] --summary requires --markdown flag")
      return

    if self.compact and not self.markdown:
      console.print("[red]Error:[/red] --compact requires --markdown flag")
      return

    if self.group_by_status and not self.markdown:
      console.print("[red]Error:[/red] --group-by-status requires --markdown flag")
      return

    try:
      if self.markdown:
        await self._show_markdown_format(console)
      else:
        await self._show_raw_api_data(console)
    except HttpError as error:
      console.print(f"[red]Google API error:[/red] {error}")
      if "401" in str(error):
        console.print("Try re-authenticating by deleting .google/token.json")
    except Exception as error:
      logger.exception(f"Error fetching tasks: {error}")
      console.print(f"[red]Unexpected error:[/red] {error}")

  async def _show_raw_api_data(self, console: Console):
    """Show raw API data similar to the scratch file."""
    from ..tasks.gtasks_api import get_service

    console.print("Getting all task lists...")
    service = get_service()

    # Get all task lists
    results = service.tasklists().list(maxResults=100).execute()
    task_lists = results.get("items", [])

    if not task_lists:
      console.print("No task lists found.")
      return

    console.print(f"\nFound {len(task_lists)} task list(s):\n")

    # For each task list, print its details and tasks
    for task_list in task_lists:
      console.print(f"[bold]Task List:[/bold] {task_list['title']}")
      console.print(f"  [dim]ID:[/dim] {task_list['id']}")
      console.print(f"  [dim]Updated:[/dim] {task_list.get('updated', 'N/A')}")

      # Get tasks for this list
      tasks_result = (
        service.tasks()
        .list(
          tasklist=task_list["id"],
          maxResults=100,
          showCompleted=self.include_completed,
          showHidden=False,
        )
        .execute()
      )
      tasks = tasks_result.get("items", [])

      if tasks:
        console.print(f"  [dim]Tasks ({len(tasks)}):[/dim]")
        for task in tasks:
          status_icon = "✅" if task.get("status") == "completed" else "⬜"
          due_str = ""
          if "due" in task:
            due_date = datetime.fromisoformat(task["due"].replace("Z", "+00:00"))
            due_str = f" [dim](Due: {due_date.strftime('%Y-%m-%d')})[/dim]"

          indent = "    "
          if "parent" in task:
            indent = "      "  # Extra indent for subtasks

          console.print(f"{indent}{status_icon} {task['title']}{due_str}")

          # Print task details if available
          if task.get("notes"):
            console.print(f"{indent}  [dim]Notes:[/dim] {task['notes']}")
          if task.get("id"):
            console.print(f"{indent}  [dim]ID:[/dim] {task['id']}")
      else:
        console.print("  [dim]No tasks in this list.[/dim]")

      console.print()  # Empty line between lists

  async def _show_markdown_format(self, console: Console):
    """Show enhanced markdown formatting using our models."""
    from ..tasks.gtasks_api import task_lists_in_range
    from ..tasks.model import TasksOfInterest

    # Calculate date range
    now = datetime.now()
    if self.start_date:
      start_ts = datetime.combine(self.start_date, datetime.min.time())
    else:
      start_ts = now - timedelta(days=30)  # Default: 30 days ago

    if self.end_date:
      end_ts = datetime.combine(self.end_date, datetime.max.time())
    else:
      end_ts = now + timedelta(days=30)  # Default: 30 days ahead

    console.print(f"Fetching tasks from {start_ts.date()} to {end_ts.date()}...")

    # Use our enhanced API to fetch task lists
    task_lists = task_lists_in_range(
      briefing_date=now, start_ts=start_ts, end_ts=end_ts, show_completed=self.include_completed
    )

    if not task_lists:
      console.print("No task lists found in the specified date range.")
      return

    # Create TasksOfInterest object
    tasks_of_interest = TasksOfInterest(task_lists_by_id={tl.id: tl for tl in task_lists})

    # Generate markdown based on flags
    markdown_output = tasks_of_interest.model_dump_markdown(
      briefing_date=now,
      compact=self.compact,
      group_by_status=self.group_by_status,
      summary_only=self.summary,
      show_colloquial=False,  # Don't show colloquial dates in CLI
    )

    # Print markdown (rich will handle markdown rendering)
    console.print(Markdown(markdown_output))
