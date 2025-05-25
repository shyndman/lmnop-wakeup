from datetime import date

import rich
from langchain_core.runnables import RunnableConfig
from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph
from pydantic import BaseModel

from lmnop_wakeup import APP_DIRS
from lmnop_wakeup.events.model import CalendarSet


class State(BaseModel):
  briefing_date: date
  events: CalendarSet | None = None
  # weather: WeatherSet
  # schedule: Schedule


async def write_briefing_script(state: State) -> State:
  return state


async def write_briefing_outline(state: State) -> State:
  return state


async def prioritize_events(state: State) -> State:
  return state


async def calculate_schedule(state: State) -> State:
  return state


# tools:
# - weather summary (from: datetime, to): str


async def request_weather(state: State) -> State:
  return state


async def resolve_location(state: State) -> State:
  return state


# tools:
# - geocode(AddressLocation): CoordinateLocation


async def populate_raw_inputs(state: State) -> State:
  return state


builder = StateGraph(State)
builder.set_entry_point("populate_raw_inputs")
builder.set_finish_point("expensive_node")


async def run_briefing_workflow(briefing_date: date) -> None:
  """Run the morning briefing workflow.

  Args:
      briefing_date: The date for which to run the briefing.
  """
  async with AsyncSqliteSaver.from_conn_string(
    str(APP_DIRS.user_cache_path / "cache.db"),
  ) as saver:
    graph = builder.compile(
      cache=InMemoryCache(),
      checkpointer=saver,
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    for _ in range(3):
      # Run the workflow with a state update
      rich.print(
        await graph.ainvoke(
          input=State(briefing_date=briefing_date),
          config=config,
          stream_mode="updates",
        )
      )

  # Run the workflow
  # await workflow.run(briefing_date)
