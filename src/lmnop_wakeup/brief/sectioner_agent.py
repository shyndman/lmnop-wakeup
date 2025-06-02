# from typing import override


from datetime import timedelta
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, RootModel
from pydantic.dataclasses import dataclass

from lmnop_wakeup.weather.sunset_oracle_agent import SunsetPrediction

from ..events.model import CalendarEvent
from ..events.prioritizer_agent import PrioritizedEvents
from ..events.scheduler_agent import Schedule
from ..llm import LangfuseAgentInput, LmnopAgent, ModelName, extract_pydantic_ai_callback
from ..weather.model import RegionalWeatherReports


class _CalendarEventList(RootModel[list[CalendarEvent]]):
  root: list[CalendarEvent]


class SectionerInput(LangfuseAgentInput):
  """Input for the sectioner agent."""

  schedule: Schedule
  prioritized_events: PrioritizedEvents
  regional_weather_reports: RegionalWeatherReports
  sunset_predication: SunsetPrediction

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
    }


@dataclass
class EventBriefEstimation:
  id: str = Field(..., description="The CalendarEvent's id field.")

  summary: str = Field(..., description="The summary taken from the associated calendar event.")

  estimated_words: int = Field(
    ..., description="Estimated number of words for the briefing section."
  )

  rationale: str = Field(
    ..., description="Rationale for the number of words allocated to this event."
  )


class SectionerOutput(BaseModel):
  estimated_total_length: int = Field(
    ...,
    description="Estimated total length of the briefing in words.",
  )
  estimated_total_duration: timedelta = Field(
    ...,
    description="Estimated total duration of the briefing.",
  )
  must_include: list[EventBriefEstimation]
  pass


type ContentOptimizationReport = SectionerOutput

# CONTENT OPTIMIZATION REPORT

# TIME BUDGET STATUS: [OPTIMAL/TIGHT/OVER/UNDER]
# Estimated total length: [X] words ([X.X] minutes)

# MUST INCLUDE (Required):
# - [Event 1]: [estimated words] - [brief rationale]
# - [Event 2]: [estimated words] - [brief rationale]
# - Wake-up event: [estimated words]
# Total required: [X] words

# RECOMMENDED ADDITIONS from could_mention:
# - [Event A]: [estimated words] - [why include]
# - [Event B]: [estimated words] - [why include]
# Total recommended: [X] words

# SKIP FOR TIME:
# - [Event C]: [reason to skip]
# - [Event D]: [reason to skip]

# TRAVEL TIMING NOTES:
# - [Include/Skip travel mentions] - [reasoning]

# PACING SUGGESTIONS:
# - [Any specific recommendations for handling tight/loose timing]
# - [Suggestions for natural content groupings]

# ALTERNATIVE SCENARIOS:
# If running long: [which could_mention items to cut first]
# If running short: [which deprioritized items could be rescued]


type BriefingOutline = SectionerOutput

type SectionerAgent = LmnopAgent[SectionerInput, SectionerOutput]


def get_sectioner_agent(config: RunnableConfig) -> SectionerAgent:
  """Get the sectioner agent."""

  agent = LmnopAgent[SectionerInput, SectionerOutput].create(
    "sectioner",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=SectionerInput,
    output_type=SectionerOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  return agent
