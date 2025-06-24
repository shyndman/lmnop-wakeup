"""Pydantic models for task management."""

import textwrap
from collections.abc import Generator
from datetime import datetime
from io import StringIO
from typing import Any, Literal, NewType

from pydantic import AwareDatetime, BaseModel, Field

from ..core.date import TimeInfo, format_time_info, start_of_local_day
from ..core.typing import assert_not_none

TaskId = NewType("TaskId", str)
TaskListId = NewType("TaskListId", str)


class Task(BaseModel):
  """Represents a single task."""

  id: TaskId
  """Uniquely identifies the task."""

  title: str
  """The title of the task."""

  notes: str | None = None
  """Notes describing the task."""

  status: Literal["needsAction", "completed"]
  """Status of the task."""

  due: TimeInfo | None = None
  """Due date of the task."""

  updated: AwareDatetime
  """Last modification time of the task."""

  completed: AwareDatetime | None = None
  """Completion date of the task (only present if status is 'completed')."""

  parent: TaskId | None = None
  """Parent task ID if this is a subtask."""

  position: str | None = None
  """Position of the task in the task list."""

  when_colloquial: list[str] = Field(
    default=[],
    description="Natural-sounding terms that can be used to refer to this task's due date, "
    "such as 'tomorrow', 'next week', 'in 3 days' - helps script writers sound "
    "conversational when mentioning the task",
  )

  priority: Literal["high", "medium", "low"] | None = None
  """Priority level of the task (inferred from title/notes if not explicitly set)."""

  def is_overdue(self, as_of: datetime) -> bool:
    """Check if the task is overdue as of the given datetime."""
    if self.due is None or self.status == "completed":
      return False
    due_date = self.due.date if self.due.date else self.due.to_aware_datetime().date()
    return due_date < as_of.date()

  def days_overdue(self, as_of: datetime) -> int:
    """Return the number of days this task is overdue (0 if not overdue)."""
    if not self.is_overdue(as_of):
      return 0
    due = assert_not_none(self.due)
    due_date = due.date if due.date else due.to_aware_datetime().date()
    return (as_of.date() - due_date).days

  def priority_icon(self) -> str:
    """Return priority icon based on priority level."""
    if self.priority == "high":
      return "🔴"
    elif self.priority == "medium":
      return "🟡"
    elif self.priority == "low":
      return "🔵"
    return ""

  def status_icon(self) -> str:
    """Return status icon for the task."""
    return "✅" if self.status == "completed" else "⬜"

  @property
  def due_date_aware(self) -> AwareDatetime | None:
    """
    Returns the timezone-aware due datetime of the task.
    For date-only due dates, this is the start of the day.
    """
    if self.due is None:
      return None
    if self.due.date is not None:
      return start_of_local_day(self.due.date)
    return self.due.to_aware_datetime()

  def overlaps_with_range(self, range_start: AwareDatetime, range_end: AwareDatetime) -> bool:
    """
    Checks if the task's due date falls within a given range.

    Args:
        range_start: The start of the range to check against.
        range_end: The end of the range to check against.

    Returns:
        True if the task is due within the given range, False otherwise.
    """
    if self.due_date_aware is None:
      return False
    # For tasks, we check if the due date falls within the range
    return range_start <= self.due_date_aware <= range_end

  def model_dump_markdown(
    self, briefing_date: datetime, compact: bool = False, show_colloquial: bool = True
  ) -> str:
    """
    Dumps the task details in a markdown format.

    Args:
        briefing_date: The date to calculate overdue status against
        compact: If True, uses a compact single-line format
        show_colloquial: If True, includes colloquial date descriptions

    Returns:
        A string containing the task details formatted in markdown.
    """
    if compact:
      return self._format_compact(briefing_date)

    sb = StringIO()

    # Build status line with icons and priority
    status_icon = self.status_icon()
    priority_icon = self.priority_icon()

    # Enhanced overdue marker
    if self.is_overdue(briefing_date):
      days_over = self.days_overdue(briefing_date)
      if days_over == 1:
        overdue_marker = " ⚠️ **OVERDUE by 1 day**"
      else:
        overdue_marker = f" ⚠️ **OVERDUE by {days_over} days**"
    else:
      overdue_marker = ""

    # Task title with strikethrough for completed
    title = f"~~{self.title}~~" if self.status == "completed" else self.title
    priority_str = f" {priority_icon}" if priority_icon else ""

    sb.write(f"* {status_icon} **{title}**{priority_str}{overdue_marker}\n")
    sb.write("  \n")  # Blank line for spacing
    sb.write(f"  **ID:** {self.id}\n")
    sb.write("  \n")  # Blank line between ID and due date

    if self.due:
      due_str = format_time_info(self.due, "%Y-%m-%d", "%H:%M:%S")
      sb.write(f"  **Due:** {due_str}\n")

      # Add colloquial dates as simple sub-bullets only if requested
      if show_colloquial and self.when_colloquial:
        for desc in self.when_colloquial:
          sb.write(f"  - {desc}\n")

    if self.notes:
      sb.write("  **Notes:**\n")
      sb.write(f"  {self.notes}\n")

    if self.completed:
      sb.write(f"  **Completed:** {self.completed.strftime('%Y-%m-%d %H:%M:%S')}\n")

    sb.write("\n")
    return sb.getvalue()

  def _format_compact(self, briefing_date: datetime) -> str:
    """Format task in compact single-line format."""
    status_icon = self.status_icon()
    priority_icon = self.priority_icon()

    # Task title with strikethrough for completed
    title = f"~~{self.title}~~" if self.status == "completed" else self.title

    # Due date info
    due_info = ""
    if self.due and self.when_colloquial:
      # Use first colloquial description
      due_info = f" (due {self.when_colloquial[0]})"
    elif self.due:
      due_str = format_time_info(self.due, "%Y-%m-%d", "%H:%M:%S")
      due_info = f" (due {due_str})"

    # Overdue indicator
    if self.is_overdue(briefing_date):
      days_over = self.days_overdue(briefing_date)
      due_info = f" (overdue {days_over} day{'s' if days_over != 1 else ''})"

    # Completed indicator
    if self.status == "completed":
      due_info = " (completed)"

    priority_str = f" {priority_icon}" if priority_icon else ""

    return f"* {status_icon} {title}{priority_str}{due_info}\n"


class TaskList(BaseModel):
  """Represents a task list containing multiple tasks."""

  id: TaskListId
  """The unique identifier for the task list."""

  title: str
  """The title of the task list."""

  tasks: list[Task] = []
  """List of tasks in this task list."""

  notes_for_processing: str | None = None
  """Any notes relevant for processing this task list."""

  def filter_tasks_by_range(self, start_ts: AwareDatetime, end_ts: AwareDatetime) -> list[Task]:
    """
    Filters the tasks within this list to only include those that
    have due dates in the given time range.

    Args:
        start_ts: The start of the time range to filter by.
        end_ts: The end of the time range to filter by.

    Returns:
        A list of Task objects that have due dates within the given time range.
    """
    return [task for task in self.tasks if task.overlaps_with_range(start_ts, end_ts)]

  def filter_incomplete_tasks(self) -> list[Task]:
    """Returns only tasks that need action (not completed)."""
    return [task for task in self.tasks if task.status == "needsAction"]

  def model_dump_markdown(
    self,
    briefing_date: datetime,
    compact: bool = False,
    group_by_status: bool = False,
    show_colloquial: bool = True,
  ) -> str:
    """
    Converts the task list to markdown format.

    Args:
        briefing_date: Date to calculate overdue status against
        compact: If True, uses compact single-line format for tasks
        group_by_status: If True, groups tasks by status (overdue, due soon, etc.)
        show_colloquial: If True, includes colloquial date descriptions
    """
    sb = StringIO()

    # Task counts
    total_tasks = len(self.tasks)
    completed_tasks = len([t for t in self.tasks if t.status == "completed"])
    overdue_tasks = len([t for t in self.tasks if t.is_overdue(briefing_date)])
    incomplete_tasks = total_tasks - completed_tasks

    # Header with counts
    counts_str = f"{total_tasks} task{'s' if total_tasks != 1 else ''}"
    if incomplete_tasks > 0:
      counts_str += f" ({incomplete_tasks} remaining"
      if overdue_tasks > 0:
        counts_str += f", {overdue_tasks} overdue"
      counts_str += ")"

    sb.write(
      textwrap.dedent(f"""
            --------------------------------

            ## {self.title} — {counts_str}

            > {self.notes_for_processing or "No special processing notes"}


            """).lstrip()
    )

    if group_by_status:
      self._write_grouped_tasks(sb, briefing_date, compact, show_colloquial)
    else:
      self._write_hierarchical_tasks(sb, briefing_date, compact, show_colloquial)

    return sb.getvalue()

  def _write_grouped_tasks(
    self, sb: StringIO, briefing_date: datetime, compact: bool, show_colloquial: bool
  ):
    """Write tasks grouped by status."""
    from datetime import timedelta

    # Categorize tasks
    overdue = [t for t in self.tasks if t.is_overdue(briefing_date)]
    due_today = [
      t
      for t in self.tasks
      if not t.is_overdue(briefing_date)
      and t.due_date_aware
      and t.due_date_aware.date() == briefing_date.date()
      and t.status == "needsAction"
    ]
    due_soon = [
      t
      for t in self.tasks
      if not t.is_overdue(briefing_date)
      and t.due_date_aware
      and briefing_date.date()
      < t.due_date_aware.date()
      <= (briefing_date + timedelta(days=7)).date()
      and t.status == "needsAction"
    ]
    no_due_date = [t for t in self.tasks if t.due is None and t.status == "needsAction"]
    completed = [t for t in self.tasks if t.status == "completed"]

    # Write each section
    sections = [
      ("⚠️ Overdue", overdue),
      ("📅 Due Today", due_today),
      ("🔜 Due This Week", due_soon),
      ("📝 No Due Date", no_due_date),
      ("✅ Completed", completed) if not compact else ("✅ Completed", []),
    ]

    for section_title, tasks in sections:
      if tasks:
        sb.write(f"### {section_title}\n\n")
        for task in tasks:
          sb.write(task.model_dump_markdown(briefing_date, compact, show_colloquial))
        sb.write("\n")

  def _write_hierarchical_tasks(
    self, sb: StringIO, briefing_date: datetime, compact: bool, show_colloquial: bool
  ):
    """Write tasks in hierarchical format with subtasks."""
    # Group tasks by parent/subtask relationship
    root_tasks = [t for t in self.tasks if t.parent is None]
    subtasks_by_parent = {}
    for task in self.tasks:
      if task.parent:
        if task.parent not in subtasks_by_parent:
          subtasks_by_parent[task.parent] = []
        subtasks_by_parent[task.parent].append(task)

    # Write root tasks and their subtasks with tree formatting
    for task in root_tasks:
      sb.write(task.model_dump_markdown(briefing_date, compact, show_colloquial))

      # Write subtasks with tree-like formatting
      if task.id in subtasks_by_parent:
        subtasks = subtasks_by_parent[task.id]
        for i, subtask in enumerate(subtasks):
          is_last = i == len(subtasks) - 1
          prefix = "    └── " if is_last else "    ├── "

          if compact:
            # For compact format, just add the prefix
            task_line = subtask._format_compact(briefing_date).strip()
            sb.write(f"{prefix}{task_line[2:]}\n")  # Remove "* " from beginning
          else:
            # For detailed format, indent all lines
            lines = subtask.model_dump_markdown(briefing_date, compact, show_colloquial).split("\n")
            for j, line in enumerate(lines):
              if j == 0 and line.strip():
                # First line gets tree prefix
                sb.write(f"{prefix}{line[2:]}\n")  # Remove "* " from beginning
              elif line.strip():
                # Subsequent lines get continuation indent
                continuation_prefix = "        " if is_last else "    │   "
                sb.write(f"{continuation_prefix}{line}\n")
              else:
                sb.write("\n")


class TasksOfInterest(BaseModel):
  """Represents a collection of task lists."""

  task_lists_by_id: dict[TaskListId, TaskList] = {}
  """A dictionary mapping task list IDs to TaskList objects."""

  def all_tasks(self) -> Generator[Task, Any, None]:
    """Yields all tasks across all task lists."""
    for task_list in self.task_lists_by_id.values():
      for task in task_list.tasks:
        yield task

  def all_incomplete_tasks(self) -> Generator[Task, Any, None]:
    """Yields all incomplete tasks across all task lists."""
    for task in self.all_tasks():
      if task.status == "needsAction":
        yield task

  def filter(
    self,
    start_ts: AwareDatetime | None = None,
    end_ts: AwareDatetime | None = None,
    title_inclusion_list: set[str] | None = None,
    include_completed: bool = False,
  ) -> "TasksOfInterest":
    """
    Filters the task lists to match specified criteria.

    Args:
        start_ts: The start of the time range to filter by (optional).
        end_ts: The end of the time range to filter by (optional).
        title_inclusion_list: An optional set of task list titles to include.
        include_completed: Whether to include completed tasks.

    Returns:
        A new TasksOfInterest containing only the filtered task lists and their tasks.
    """
    filtered_task_lists = {}
    for list_id, task_list in self.task_lists_by_id.items():
      if title_inclusion_list is not None and task_list.title not in title_inclusion_list:
        continue

      # Filter tasks
      filtered_tasks = task_list.tasks

      # Filter by completion status
      if not include_completed:
        filtered_tasks = [t for t in filtered_tasks if t.status == "needsAction"]

      # Filter by date range if provided
      if start_ts is not None and end_ts is not None:
        filtered_tasks = [
          t for t in filtered_tasks if t.due is None or t.overlaps_with_range(start_ts, end_ts)
        ]

      if filtered_tasks:
        filtered_list = task_list.model_copy(deep=True)
        filtered_list.tasks = filtered_tasks
        filtered_task_lists[list_id] = filtered_list

    return TasksOfInterest(task_lists_by_id=filtered_task_lists)

  def filter_by_task_ids(self, task_ids: set[TaskId]) -> "TasksOfInterest":
    """
    Returns a copy of TasksOfInterest containing only the specified tasks
    and their associated task lists.

    Args:
        task_ids: Set of task IDs to include in the filtered result

    Returns:
        A new TasksOfInterest with only the specified tasks and task lists
        that contain those tasks
    """
    filtered_task_lists = {}

    for list_id, task_list in self.task_lists_by_id.items():
      # Filter tasks to only include those in the task_ids set
      filtered_tasks = [task for task in task_list.tasks if task.id in task_ids]

      # Only include task lists that have at least one matching task
      if filtered_tasks:
        filtered_list = task_list.model_copy(deep=True)
        filtered_list.tasks = filtered_tasks
        filtered_task_lists[list_id] = filtered_list

    return TasksOfInterest(task_lists_by_id=filtered_task_lists)

  def model_dump_markdown(
    self,
    briefing_date: datetime,
    compact: bool = False,
    group_by_status: bool = False,
    summary_only: bool = False,
    show_colloquial: bool = True,
  ) -> str:
    """
    Converts all task lists to markdown format.

    Args:
        briefing_date: Date to calculate overdue status against
        compact: If True, uses compact single-line format for tasks
        group_by_status: If True, groups tasks by status within each list
        summary_only: If True, shows only summary stats for each list
        show_colloquial: If True, includes colloquial date descriptions
    """
    sb = StringIO()

    if summary_only:
      return self._format_summary(briefing_date)

    # Overall summary
    total_lists = len(self.task_lists_by_id)
    total_tasks = sum(len(tl.tasks) for tl in self.task_lists_by_id.values())
    total_overdue = sum(
      len([t for t in tl.tasks if t.is_overdue(briefing_date)])
      for tl in self.task_lists_by_id.values()
    )
    total_incomplete = sum(
      len([t for t in tl.tasks if t.status == "needsAction"])
      for tl in self.task_lists_by_id.values()
    )

    sb.write("# Task Lists Overview\n\n")
    sb.write(f"**{total_lists} list{'s' if total_lists != 1 else ''}** • ")
    sb.write(f"**{total_tasks} task{'s' if total_tasks != 1 else ''}** • ")
    sb.write(f"**{total_incomplete} remaining**")
    if total_overdue > 0:
      sb.write(f" • ⚠️ **{total_overdue} overdue**")
    sb.write("\n\n")

    # Individual task lists
    for task_list in self.task_lists_by_id.values():
      if not task_list.tasks:
        continue

      sb.write(
        task_list.model_dump_markdown(briefing_date, compact, group_by_status, show_colloquial)
      )

    return sb.getvalue()

  def _format_summary(self, briefing_date: datetime) -> str:
    """Format a compact summary of all task lists."""
    sb = StringIO()
    sb.write("# Task Lists Summary\n\n")

    for task_list in self.task_lists_by_id.values():
      if not task_list.tasks:
        continue

      total_tasks = len(task_list.tasks)
      completed_tasks = len([t for t in task_list.tasks if t.status == "completed"])
      overdue_tasks = len([t for t in task_list.tasks if t.is_overdue(briefing_date)])
      incomplete_tasks = total_tasks - completed_tasks

      # Status indicators
      status_indicators = []
      if overdue_tasks > 0:
        status_indicators.append(f"⚠️ {overdue_tasks} overdue")
      if incomplete_tasks > 0:
        status_indicators.append(f"📝 {incomplete_tasks} remaining")
      if completed_tasks == total_tasks and total_tasks > 0:
        status_indicators.append("✅ all complete")

      status_str = " • ".join(status_indicators) if status_indicators else "📝 empty"

      task_count = f"{total_tasks} task{'s' if total_tasks != 1 else ''}"
      sb.write(f"- **{task_list.title}**: {task_count} • {status_str}\n")

    return sb.getvalue()
