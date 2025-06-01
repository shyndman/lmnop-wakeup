from typing import override

from pydantic import RootModel

from ..events.model import Schedule
from ..llm import (
  LangfuseAgent,
  LangfuseAgentInput,
  ModelName,
  RunnableConfig,
  extract_pydantic_ai_callback,
)
from ..weather.meteorologist_agent import WeatherAnalysis
from ..weather.sunset_oracle_agent import SunsetPrediction
from .model import BriefingScript, CharacterPool
from .sectioner_agent import BriefingOutline, PrioritizedEvents


class PreviousScripts(RootModel[list[BriefingScript]]):
  root: list[BriefingScript]


class ScriptWriterInput(LangfuseAgentInput):
  briefing_outline: BriefingOutline
  prioritized_events: PrioritizedEvents
  schedule: Schedule
  weather_report: WeatherAnalysis
  sunset_prediction: SunsetPrediction
  character_pool: CharacterPool
  previous_scripts: list[BriefingScript]

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    return {
      "briefing_outline": self.briefing_outline.model_dump_json(),
      "schedule": self.schedule.model_dump_json(),
      "prioritized_events": self.prioritized_events.model_dump_json(),
      "weather_report": self.weather_report.model_dump_json(),
      "sunset_prediction": self.sunset_prediction.model_dump_json(),
      "character_pool": self.character_pool.model_dump_json(),
      "previous_scripts": PreviousScripts(self.previous_scripts).model_dump_json(),
    }


ScriptWriterOutput = BriefingScript


type ScriptWriterAgent = LangfuseAgent[ScriptWriterInput, ScriptWriterOutput]


def get_script_writer_agent(config: RunnableConfig) -> ScriptWriterAgent:
  """Get the script_writer agent."""

  agent = LangfuseAgent[ScriptWriterInput, ScriptWriterOutput].create(
    "script_writer",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=ScriptWriterInput,
    output_type=ScriptWriterOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  return agent
