from typing import override

from pydantic import RootModel

from ..events.model import CalendarsOfInterest, Schedule, start_of_local_day
from ..llm import (
  LangfuseAgentInput,
  LmnopAgent,
  ModelName,
  RunnableConfig,
  extract_pydantic_ai_callback,
)
from ..weather.meteorologist_agent import WeatherAnalysis
from ..weather.sunset_oracle_agent import SunsetPrediction
from .content_optimizer import ContentOptimizationReport, PrioritizedEvents
from .model import BriefingScript, CharacterPool


class PreviousScripts(RootModel[list[BriefingScript]]):
  root: list[BriefingScript]


class ScriptWriterInput(LangfuseAgentInput):
  content_optimizer_report: ContentOptimizationReport
  prioritized_events: PrioritizedEvents
  schedule: Schedule
  weather_report: WeatherAnalysis
  sunset_prediction: SunsetPrediction
  character_pool: CharacterPool
  previous_scripts: list[BriefingScript]
  calendars_of_interest: CalendarsOfInterest

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    filtered_content_optimizer_report = self.content_optimizer_report.filter_zero_priority_skipped()

    # Filter calendars to only include events mentioned in the content optimization report
    filtered_calendars = self.calendars_of_interest.filter_by_event_ids(
      filtered_content_optimizer_report.event_ids
    )

    return {
      "content_optimizer_report": filtered_content_optimizer_report.model_dump_json(),
      "schedule": self.schedule.model_dump_json(),
      "prioritized_events": self.prioritized_events.model_dump_json(exclude={"deprioritized"}),
      "weather_report": self.weather_report.model_dump_json(exclude={"reports_by_location"}),
      "sunset_prediction": self.sunset_prediction.model_dump_json(),
      "events_of_interest": filtered_calendars.model_dump_markdown(
        start_of_local_day(self.schedule.date)
      ),
      "character_pool": self.character_pool.model_dump_json(),
      "previous_scripts": PreviousScripts(self.previous_scripts).model_dump_json(),
    }


ScriptWriterOutput = BriefingScript


type ScriptWriterAgent = LmnopAgent[ScriptWriterInput, ScriptWriterOutput]


def get_script_writer_agent(config: RunnableConfig) -> ScriptWriterAgent:
  """Get the script_writer agent."""

  agent = LmnopAgent[ScriptWriterInput, ScriptWriterOutput].create(
    "script_writer",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=ScriptWriterInput,
    output_type=ScriptWriterOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  return agent
