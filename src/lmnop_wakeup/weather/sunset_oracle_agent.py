import textwrap
from enum import StrEnum, auto
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import AwareDatetime, BaseModel

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
    # mcp_servers=[sandboxed_python_mcp_server()],
  )

  return agent
