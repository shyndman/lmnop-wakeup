import itertools
import textwrap
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import AwareDatetime, RootModel

from pirate_weather_api_client.models import AlertsItem

from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName, extract_pydantic_ai_callback
from .model import WeatherAnalysis, WeatherReport


class AlertList(RootModel[list[AlertsItem]]):
  root: list[AlertsItem]


class MeteorologistInput(LangfuseAgentInput):
  """Input data for the meteorologist agent."""

  report_date: AwareDatetime
  """The date this report is being delivered, in the user's timezone."""

  weather_report: list[WeatherReport]
  """The list of weather reports that apply to the region."""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    return {
      "report_date": textwrap.dedent(f"""
        {self.report_date.strftime("%A, %B %d, %Y")}
        iso8601 format: {self.report_date.isoformat()}
        """).lstrip(),
      "weather_data": "\n".join(
        [report.weather_report_api_result for report in self.weather_report]
      ),
      "air_quality_data": "\n".join(
        [
          report.air_quality_api_result
          for report in self.weather_report
          if report.air_quality_api_result
        ]
      ),
      "alerts": AlertList(
        list(itertools.chain(*[report.alerts for report in self.weather_report]))
      ).model_dump_json(),
    }


MeteorologistOutput = WeatherAnalysis

type MeteorologistAgent = LangfuseAgent[MeteorologistInput, MeteorologistOutput]


def _get_meteorologist_agent(config: RunnableConfig) -> MeteorologistAgent:
  """Get the location resolver agent."""

  return LangfuseAgent[MeteorologistInput, MeteorologistOutput].create(
    "meteorologist",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=MeteorologistInput,
    output_type=MeteorologistOutput,
    callback=extract_pydantic_ai_callback(config),
  )


_meteorologist_agent: MeteorologistAgent | None = None


def get_meteorologist_agent(config: RunnableConfig) -> MeteorologistAgent:
  """Get the location resolver agent."""
  global _meteorologist_agent
  if _meteorologist_agent is None:
    _meteorologist_agent = _get_meteorologist_agent(config)
  return _meteorologist_agent
