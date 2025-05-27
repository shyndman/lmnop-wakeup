# from typing import override


from typing import override

from pydantic import BaseModel, Field

from ..events.model import CalendarEvent
from ..events.prioritizer_agent import PrioritizedEvents
from ..events.scheduler_agent import Schedule
from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName
from ..weather.model import RegionalWeatherReports


class SectionerInput(LangfuseAgentInput):
  """Input for the sectioner agent."""

  schedule: Schedule

  prioritized_events: PrioritizedEvents

  regional_weather_reports: RegionalWeatherReports

  yesterday_events: list[CalendarEvent]

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      k: v.model_dump_json() if v is not None else "null"
      for k, v in {
        "schedule": self.schedule,
        "prioritized_events": self.prioritized_events,
        "regional_weather_reports": self.regional_weather_reports,
        "yesterday_events": self.yesterday_events,
      }.items()
    }


class Section(BaseModel):
  title: str
  content: str


class SectionerOutput(BaseModel):
  sections: list[Section] = Field([], min_length=4)


type BriefingOutline = SectionerOutput

type SectionerAgent = LangfuseAgent[SectionerInput, SectionerOutput]


def get_sectioner_agent() -> SectionerAgent:
  """Get the sectioner agent."""

  agent = LangfuseAgent[SectionerInput, SectionerOutput].create(
    "sectioner",
    model=ModelName.GEMINI_25_PRO,
    input_type=SectionerInput,
    output_type=SectionerOutput,
  )

  return agent
