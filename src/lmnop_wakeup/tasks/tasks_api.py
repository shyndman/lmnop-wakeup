"""Higher-level API for task management with processing notes."""

from datetime import datetime
from enum import StrEnum, auto

import structlog
from langgraph.func import task
from pydantic import BaseModel

from ..core.date import end_of_local_day, start_of_local_day
from .gtasks_api import task_lists_in_range
from .model import TaskList, TasksOfInterest

logger = structlog.get_logger()


class TaskListFilter(StrEnum):
  no_filter = auto()
  today_only = auto()
  exclude_completed = auto()


class TaskListInfo(BaseModel):
  notes: str
  task_filter: TaskListFilter = TaskListFilter.exclude_completed


# Define task list processing instructions
TASKLIST_INSTRUCTIONS = {
  # Example task lists - update these with actual IDs once discovered
  "default": TaskListInfo(
    notes="This is the default task list. Tasks here are general reminders and to-dos that "
    "should be mentioned in briefings when they're due soon or overdue."
  ),
  # Add more task lists as needed, e.g.:
  # "work_tasks_list_id": TaskListInfo(
  #     notes="Work-related tasks. High priority during weekdays.",
  #     task_filter=TaskListFilter.exclude_completed,
  # ),
  # "personal_projects_list_id": TaskListInfo(
  #     notes="Personal project tasks. Medium priority, good for weekend reminders.",
  # ),
  # "shopping_list_id": TaskListInfo(
  #     notes="Shopping and errands list. Mention items due today or overdue.",
  #     task_filter=TaskListFilter.today_only,
  # ),
}


@task()
async def get_filtered_task_lists_with_notes(
  briefing_date: datetime,
  start_ts: datetime,
  end_ts: datetime,
  include_completed: bool = False,
) -> list[TaskList]:
  """
  Fetches task lists from Google Tasks, filters them based on
  TASKLIST_INSTRUCTIONS, and assigns notes for processing.

  Args:
      briefing_date: The date of the briefing
      start_ts: Start of the time range to fetch tasks
      end_ts: End of the time range to fetch tasks
      include_completed: Whether to include completed tasks

  Returns:
      List of TaskList objects with processing notes applied
  """
  logger.info(f"Fetching task lists between {start_ts} and {end_ts}")

  # Fetch all task lists from Google Tasks
  all_task_lists = task_lists_in_range(
    briefing_date=briefing_date,
    start_ts=start_ts,
    end_ts=end_ts,
    show_completed=include_completed,
  )

  logger.info(f"Fetched {len(all_task_lists)} task lists from Google Tasks")

  filtered_task_lists: list[TaskList] = []

  for task_list in all_task_lists:
    # Check if we have instructions for this list
    instructions = TASKLIST_INSTRUCTIONS.get(
      task_list.id,
      # Use default instructions if list ID not found
      TASKLIST_INSTRUCTIONS.get("default"),
    )

    if instructions is None:
      logger.info(f"Skipping task list {task_list.id} as it has no instructions")
      continue

    # Apply processing notes
    task_list.notes_for_processing = instructions.notes

    # Apply filters based on instructions
    if instructions.task_filter == TaskListFilter.today_only:
      # Filter to only include today's tasks
      task_list.tasks = [
        task
        for task in task_list.tasks
        if task.due_date_aware is not None
        and start_of_local_day(briefing_date)
        <= task.due_date_aware
        <= end_of_local_day(briefing_date)
      ]
    elif instructions.task_filter == TaskListFilter.exclude_completed:
      # Filter out completed tasks
      task_list.tasks = task_list.filter_incomplete_tasks()

    # Only include task lists that have tasks after filtering
    if task_list.tasks:
      filtered_task_lists.append(task_list)
      logger.debug(
        f"Including task list '{task_list.title}' with {len(task_list.tasks)} tasks",
        list_id=task_list.id,
        task_count=len(task_list.tasks),
      )
    else:
      logger.debug(
        f"Excluding task list '{task_list.title}' (no tasks after filtering)",
        list_id=task_list.id,
      )

  logger.info(f"Filtered task lists based on instructions. Included: {len(filtered_task_lists)}")
  return filtered_task_lists


async def get_tasks_of_interest(
  briefing_date: datetime,
  start_ts: datetime,
  end_ts: datetime,
) -> TasksOfInterest:
  """
  Convenience function to get TasksOfInterest object with filtered task lists.

  Args:
      briefing_date: The date of the briefing
      start_ts: Start of the time range to fetch tasks
      end_ts: End of the time range to fetch tasks

  Returns:
      TasksOfInterest object containing filtered task lists
  """
  task_lists = await get_filtered_task_lists_with_notes(
    briefing_date=briefing_date,
    start_ts=start_ts,
    end_ts=end_ts,
    include_completed=False,
  )

  return TasksOfInterest(task_lists_by_id={task_list.id: task_list for task_list in task_lists})
