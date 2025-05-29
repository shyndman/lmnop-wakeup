from enum import StrEnum, auto
from typing import override

from pydantic import AwareDatetime, BaseModel

from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName


class SunsetOracleInput(LangfuseAgentInput):
  """Input for the location resolver agent."""

  weather_report: str
  """A weather report received via get_sunset_weather_data"""

  air_quality_report: str
  """An air quality report received via get_sunset_weather_data"""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
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


type SunsetOracleAgent = LangfuseAgent[SunsetOracleInput, SunsetOracleOutput]


def get_sunset_oracle_agent() -> SunsetOracleAgent:
  """Get the location resolver agent."""

  agent = LangfuseAgent[SunsetOracleInput, SunsetOracleOutput].create(
    "sunset_oracle",
    model=ModelName.GEMINI_25_FLASH,
    input_type=SunsetOracleInput,
    output_type=SunsetOracleOutput,
  )

  return agent
