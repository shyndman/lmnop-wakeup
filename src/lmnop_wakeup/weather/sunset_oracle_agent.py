import textwrap
from enum import StrEnum, auto
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import AwareDatetime, BaseModel

from lmnop_wakeup.tools.run_python import run_code

from ..llm import LangfuseAgentInput, LmnopAgent, ModelName, extract_pydantic_ai_callback


class SunsetOracleInput(LangfuseAgentInput):
  """Input for the location resolver agent."""

  prediction_date: AwareDatetime
  """The date of prediction, at midnight, in the user's timezone."""

  weather_report: str
  """A weather report received via get_sunset_weather_data"""

  air_quality_report: str
  """An air quality report received via get_sunset_weather_data"""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "prediction_date": textwrap.dedent(f"""
        {self.prediction_date.strftime("%A, %B %d, %Y")}
        iso8601 format: {self.prediction_date.isoformat()}
        """).lstrip(),
      "weather_report": self.weather_report,
      "air_quality_report": self.air_quality_report,
    }


class SunsetQuality(StrEnum):
  """Enumeration of sunset quality ratings from exceptional to awful."""

  exceptional = auto()
  """Spectacular sunset conditions with optimal cloud formations (80-100)."""

  very_good = auto()
  """Beautiful sunset expected with favorable conditions (65-79)."""

  good = auto()
  """Pleasant sunset viewing with decent color potential (50-64)."""

  fair = auto()
  """Mediocre conditions, sunset visible but may lack drama (35-49)."""

  poor = auto()
  """Suboptimal viewing, limited color or partial obstruction (20-34)."""

  awful = auto()
  """Sunset likely obscured or completely blocked (0-19)."""


type SunsetPrediction = SunsetOracleOutput


class SunsetOracleOutput(BaseModel):
  """Structured output for sunset quality assessments following the required format."""

  best_viewing_time: AwareDatetime
  """Optimal datetime for sunset viewing (corresponds to "specific best viewing time
  recommendation")."""

  overall_rating: int
  """Numeric peak score representing sunset quality (part of "overall rating and peak score")."""

  quality: SunsetQuality
  """Categorical quality rating (part of overall assessment)."""

  abbreviated_assessment: str
  """One-sentence bottom line assessment for executive summary."""

  detailed_analysis: str
  """Hour-by-hour breakdown, weather patterns, and optimal viewing window justification."""


type SunsetOracleAgent = LmnopAgent[SunsetOracleInput, SunsetOracleOutput]


def get_sunset_oracle_agent(config: RunnableConfig) -> SunsetOracleAgent:
  """Get the location resolver agent."""

  agent = LmnopAgent[SunsetOracleInput, SunsetOracleOutput].create(
    "sunset_oracle",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=SunsetOracleInput,
    output_type=SunsetOracleOutput,
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
