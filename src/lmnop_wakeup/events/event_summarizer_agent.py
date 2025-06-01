# from typing import override


from typing import override

from pydantic import BaseModel

from ..llm import (
  LangfuseAgentInput,
  LmnopAgent,
  ModelName,
  RunnableConfig,
  extract_pydantic_ai_callback,
)


class EventSummarizerInput(LangfuseAgentInput):
  """Input for the event summarizer agent."""

  description: str

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {"description": self.description}


class EventSummarizerOutput(BaseModel):
  summary: str
  """1-2 sentences describing the activity"""

  category: str
  """Single category name"""

  address: str | None = None
  """Full address or None if not specified"""

  intended_audience: str
  """Any restrictions, prerequisites, or target audience"""


type EventSummarizerAgent = LmnopAgent[EventSummarizerInput, EventSummarizerOutput]


def get_event_summarizer_agent(config: RunnableConfig | None = None) -> EventSummarizerAgent:
  """Get the event summar agent."""

  agent = LmnopAgent[EventSummarizerInput, EventSummarizerOutput].create(
    "event_summarizer",
    model_name=ModelName.GEMINI_20_FLASH_LITE,
    input_type=EventSummarizerInput,
    output_type=EventSummarizerOutput,
    callback=extract_pydantic_ai_callback(config) if config else None,
  )

  return agent
