"""Google Tasks API client."""

from datetime import datetime

import structlog
from googleapiclient.discovery import build

from lmnop_wakeup.core.date import TimeInfo
from lmnop_wakeup.core.relative_dates import format_relative_date

from ..core.tracing import trace_sync
from ..tools.google_auth import authenticate
from .model import Task, TaskId, TaskList, TaskListId

logger = structlog.get_logger()


def _format_datetime_for_api(dt: datetime) -> str:
  """Format datetime for Google Tasks API.

  If datetime has timezone info, use as-is.
  Otherwise append 'Z' for UTC.
  """
  if dt.tzinfo is not None:
    return dt.isoformat()
  else:
    return dt.isoformat() + "Z"


def get_service():
  """Get authenticated Google Tasks service."""
  return build("tasks", "v1", credentials=authenticate())


@trace_sync(name="api: gtasks.get_task_lists")
def get_task_lists() -> list[dict]:
  """Fetch all task lists from Google Tasks."""
  service = get_service()

  result = service.tasklists().list(maxResults=100).execute()
  task_lists = result.get("items", [])

  # Handle pagination if needed
  while "nextPageToken" in result:
    result = service.tasklists().list(maxResults=100, pageToken=result["nextPageToken"]).execute()
    task_lists.extend(result.get("items", []))

  return task_lists


@trace_sync(name="api: gtasks.get_tasks_in_list")
def get_tasks_in_list(
  list_id: str,
  due_min: datetime | None = None,
  due_max: datetime | None = None,
  show_completed: bool = False,
) -> list[dict]:
  """
  Fetch tasks from a specific task list.

  Args:
      list_id: The ID of the task list
      due_min: Optional minimum due date filter
      due_max: Optional maximum due date filter
      show_completed: Whether to include completed tasks

  Returns:
      List of task dictionaries from the API
  """
  service = get_service()

  # Build request parameters
  params = {
    "tasklist": list_id,
    "maxResults": 100,
    "showCompleted": show_completed,
    "showHidden": False,
  }

  if due_min:
    params["dueMin"] = _format_datetime_for_api(due_min)
  if due_max:
    params["dueMax"] = _format_datetime_for_api(due_max)

  result = service.tasks().list(**params).execute()
  tasks = result.get("items", [])

  # Handle pagination
  while "nextPageToken" in result:
    params["pageToken"] = result["nextPageToken"]
    result = service.tasks().list(**params).execute()
    tasks.extend(result.get("items", []))

  return tasks


def _parse_task_from_api(raw_task: dict, briefing_date: datetime) -> Task:
  """Parse a raw task from the API into our Task model."""
  # Parse due date if present
  due_info = None
  if "due" in raw_task:
    # Google Tasks API returns due dates as RFC 3339 timestamps
    # but only the date portion is significant
    due_datetime = datetime.fromisoformat(raw_task["due"].replace("Z", "+00:00"))
    due_info = TimeInfo(date=due_datetime.date())

  # Parse other datetime fields
  updated = datetime.fromisoformat(raw_task["updated"].replace("Z", "+00:00"))
  completed = None
  if "completed" in raw_task:
    completed = datetime.fromisoformat(raw_task["completed"].replace("Z", "+00:00"))

  task = Task(
    id=TaskId(raw_task["id"]),
    title=raw_task["title"],
    notes=raw_task.get("notes"),
    status=raw_task["status"],
    due=due_info,
    updated=updated,
    completed=completed,
    parent=TaskId(raw_task["parent"]) if "parent" in raw_task else None,
    position=raw_task.get("position"),
  )

  # Generate colloquial date descriptions
  if task.due_date_aware:
    task.when_colloquial = format_relative_date(briefing_date.date(), task.due_date_aware)

  return task


@trace_sync(name="api: gtasks.task_lists_in_range")
def task_lists_in_range(
  briefing_date: datetime,
  start_ts: datetime,
  end_ts: datetime,
  show_completed: bool = False,
) -> list[TaskList]:
  """
  Fetch all task lists and their tasks within a date range.

  Args:
      briefing_date: The date of the briefing (for colloquial date formatting)
      start_ts: Start of the date range
      end_ts: End of the date range
      show_completed: Whether to include completed tasks

  Returns:
      List of TaskList objects with their tasks
  """
  # Get all task lists
  raw_lists = get_task_lists()
  task_lists = []

  for raw_list in raw_lists:
    list_id = raw_list["id"]

    # Get tasks for this list
    raw_tasks = get_tasks_in_list(
      list_id,
      due_min=start_ts,
      due_max=end_ts,
      show_completed=show_completed,
    )

    # Also get tasks without due dates (they might be relevant)
    no_due_tasks = get_tasks_in_list(
      list_id,
      show_completed=show_completed,
    )

    # Filter no_due_tasks to only include those without due dates
    no_due_tasks = [t for t in no_due_tasks if "due" not in t]

    # Combine and deduplicate
    all_task_ids = {t["id"] for t in raw_tasks}
    for task in no_due_tasks:
      if task["id"] not in all_task_ids:
        raw_tasks.append(task)

    # Parse tasks
    tasks = [_parse_task_from_api(raw_task, briefing_date) for raw_task in raw_tasks]

    # Create TaskList
    task_list = TaskList(
      id=TaskListId(list_id),
      title=raw_list["title"],
      tasks=tasks,
    )

    task_lists.append(task_list)

    logger.debug(
      f"Fetched {len(tasks)} tasks from list '{raw_list['title']}'",
      list_id=list_id,
      task_count=len(tasks),
    )

  return task_lists


def get_task(task_list_id: str, task_id: str) -> Task | None:
  """
  Retrieve a specific task.

  Args:
      task_list_id: The ID of the task list containing the task
      task_id: The ID of the task to retrieve

  Returns:
      Task object if found, None otherwise
  """
  service = get_service()
  try:
    raw_task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
    return _parse_task_from_api(raw_task, datetime.now())
  except Exception as e:
    logger.error(f"Failed to retrieve task {task_id} from list {task_list_id}: {e}")
    return None
