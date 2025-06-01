# from typing import override


from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, RootModel

from lmnop_wakeup.weather.sunset_oracle_agent import SunsetPrediction

from ..events.model import CalendarEvent
from ..events.prioritizer_agent import PrioritizedEvents
from ..events.scheduler_agent import Schedule
from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName, extract_pydantic_ai_callback
from ..weather.model import RegionalWeatherReports


class _CalendarEventList(RootModel[list[CalendarEvent]]):
  root: list[CalendarEvent]


class SectionerInput(LangfuseAgentInput):
  """Input for the sectioner agent."""

  schedule: Schedule
  prioritized_events: PrioritizedEvents
  regional_weather_reports: RegionalWeatherReports
  sunset_predication: SunsetPrediction
  yesterdays_events: list[CalendarEvent]

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "schedule": self.schedule.model_dump_json(),
      "prioritized_events": self.prioritized_events.model_dump_json(),
      "regional_weather_reports": self.regional_weather_reports.model_dump_json(
        exclude={"reports_by_location"}
      ),
      "sunset_predication": self.sunset_predication.model_dump_json(),
      "yesterdays_events": _CalendarEventList(self.yesterdays_events).model_dump_json(indent=2)
      if self.yesterdays_events
      else "[]",
    }


class Section(BaseModel):
  title: str
  content: str


class SectionerOutput(BaseModel):
  sections: list[Section] = Field([], min_length=4)


type BriefingOutline = SectionerOutput

type SectionerAgent = LangfuseAgent[SectionerInput, SectionerOutput]


def get_sectioner_agent(config: RunnableConfig) -> SectionerAgent:
  """Get the sectioner agent."""

  agent = LangfuseAgent[SectionerInput, SectionerOutput].create(
    "sectioner",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=SectionerInput,
    output_type=SectionerOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  return agent
