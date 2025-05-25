import time
from datetime import date

import rich
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph
from langgraph.types import CachePolicy
from pydantic import BaseModel

from lmnop_wakeup import APP_DIRS


class State(BaseModel):
  x: int
  result: int


builder = StateGraph(State)


def expensive_node(state: State) -> dict[str, int]:
  # expensive computation
  time.sleep(2)
  return {"result": state.x * 2}


builder.add_node("expensive_node", expensive_node, cache_policy=CachePolicy(ttl=3))
builder.set_entry_point("expensive_node")
builder.set_finish_point("expensive_node")


async def run_briefing_workflow(briefing_date: date) -> None:
  """Run the morning briefing workflow.

  Args:
      briefing_date: The date for which to run the briefing.
  """
  print(str(APP_DIRS.user_cache_path / "cache.db"))
  async with AsyncSqliteSaver.from_conn_string(
    str(APP_DIRS.user_cache_path / "cache.db"),
  ) as saver:
    graph = builder.compile(checkpointer=saver)
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    rich.print(
      await graph.ainvoke(input=State(x=5, result=-1), config=config, stream_mode="updates")
    )

  # Run the workflow
  # await workflow.run(briefing_date)
