import asyncio
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.func import entrypoint, task
from langgraph.types import interrupt
from loguru import logger

from lmnop_wakeup.utils.logging import rich_sprint


@task
async def write_essay(topic: str) -> str:
  """Write an essay about the given topic."""
  await asyncio.sleep(1)
  return f"An essay about topic: {topic}"


class MorningBriefing(TypedDict):
  pass


@entrypoint(checkpointer=MemorySaver())
async def _start_briefing_workflow(topic: str) -> MorningBriefing:
  """A simple workflow that writes an essay and asks for a review."""
  essay = write_essay("cat").result()
  is_approved = interrupt(
    {
      # Any json-serializable payload provided to interrupt as argument.
      # It will be surfaced on the client side as an Interrupt when streaming data
      # from the workflow.
      "essay": essay,  # The essay we want reviewed.
      # We can add any additional information that we need.
      # For example, introduce a key called "action" with some instructions.
      "action": "Please approve/reject the essay",
    }
  )

  return {
    "is_approved": is_approved,  # Response from HIL
  }


config = {"configurable": {"thread_id": "some_thread_id"}}


async def run(thread_id: str) -> None:
  config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
  result = await _start_briefing_workflow.ainvoke(None, config)
  logger.info("Briefing result:\n\n{result}", result=rich_sprint(result))
