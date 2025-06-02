import itertools
import textwrap
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import AwareDatetime, RootModel

from lmnop_wakeup.tools.run_python import run_code
from pirate_weather_api_client.models import AlertsItem

from ..llm import LangfuseAgentInput, LmnopAgent, ModelName, extract_pydantic_ai_callback
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

type MeteorologistAgent = LmnopAgent[MeteorologistInput, MeteorologistOutput]


def _get_meteorologist_agent(config: RunnableConfig) -> MeteorologistAgent:
  """Get the location resolver agent."""

  agent = LmnopAgent[MeteorologistInput, MeteorologistOutput].create(
    "meteorologist",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=MeteorologistInput,
    output_type=MeteorologistOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  @agent.tool_plain
  def execute_python(code: str, libraries: list[str]) -> str:
    """
    Execute Python code to analyze weather and air quality data for sunset quality prediction.

    This tool allows the agent to perform complex calculations and data analysis to determine
    whether upcoming sunsets will be visually appealing based on meteorological conditions.

    The agent can use this function to:
    - Process weather forecast data (cloud cover, humidity, visibility, wind patterns)
    - Analyze air quality metrics (PM2.5, PM10, ozone levels, atmospheric particles)
    - Generate visualizations of data trends or predictions
    - Implement sunset quality scoring algorithms

    Pre-installed libraries:
    - numpy: For numerical computations, array operations, and mathematical functions
    - plotly: For creating interactive charts and visualizations of weather/air quality data

    Args:
        code (str): Python code to execute. Should be well-structured and include proper
          error handling. The code can define functions, perform calculations,
          create visualizations, or analyze datasets related to sunset prediction.
        libraries (list[str]): Additional Python libraries to install before code execution.
          Common useful libraries for this context might include:
          - 'pandas' for data manipulation and analysis
          - 'scipy' for scientific computing and statistics
          - 'matplotlib' for additional plotting capabilities
          - 'datetime' for time-based calculations (though this is built-in)
          - 'math' for mathematical operations (though this is built-in)

    Returns:
      str: The output from the executed code, including any print statements, calculation
            results, error messages, or data summaries. If the code generates plots with
            plotly, the visualization data will be included in the response.

    Usage Example:
      To analyze whether tonight's sunset will be spectacular based on low humidity,
      moderate cloud cover, and good air quality:

      code = '''
      import numpy as np

      # Weather conditions
      humidity = 45  # %
      cloud_cover = 30  # %
      visibility = 15  # km
      pm25 = 8  # μg/m³

      # Simple sunset quality scoring
      humidity_score = max(0, (70 - humidity) / 70)  # Lower humidity = better
      cloud_score = 1 - abs(cloud_cover - 40) / 40   # ~40% clouds optimal
      visibility_score = min(visibility / 20, 1)      # Better visibility = better
      air_quality_score = max(0, (50 - pm25) / 50)   # Lower PM2.5 = better

      sunset_quality = (humidity_score + cloud_score + visibility_score + air_quality_score) / 4

      print(f"Sunset Quality Score: {sunset_quality:.2f}")
      if sunset_quality > 0.7:
          print("Excellent sunset conditions expected!")
      elif sunset_quality > 0.5:
          print("Good sunset conditions expected.")
      else:
          print("Fair sunset conditions.")
      '''

      result = execute_python(code, ["pandas"])

    Note: The execution environment is sandboxed and secure. Code should focus on data
          analysis and calculation rather than system operations or file manipulation.
    """
    return run_code("python", code, libraries=["numpy", "plotly"] + libraries, verbose=True)

  return agent


_meteorologist_agent: MeteorologistAgent | None = None


def get_meteorologist_agent(config: RunnableConfig) -> MeteorologistAgent:
  """Get the location resolver agent."""
  global _meteorologist_agent
  if _meteorologist_agent is None:
    _meteorologist_agent = _get_meteorologist_agent(config)
  return _meteorologist_agent
