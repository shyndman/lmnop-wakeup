import textwrap
from enum import StrEnum, auto
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import AwareDatetime, BaseModel

from lmnop_wakeup.weather.sunset_scoring import SunsetAnalysisResult

from ..llm import LangfuseAgentInput, LmnopAgent, ModelName, extract_pydantic_ai_callback


class SunsetOracleInput(LangfuseAgentInput):
  """Input for the location resolver agent."""

  prediction_date: AwareDatetime
  """The date of prediction, at midnight, in the user's timezone."""

  sunset_analysis: SunsetAnalysisResult
  """The result of a procedural scoring applied to detailed weather and air quality data"""

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "prediction_date": textwrap.dedent(f"""
        {self.prediction_date.strftime("%A, %B %d, %Y")}
        iso8601 format: {self.prediction_date.isoformat()}
        """).lstrip(),
      "sunset_analysis": self.sunset_analysis.model_dump_json(indent=2),
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

  abbreviated_assessment: str
  """One-sentence bottom line assessment for executive summary.

  Example: "Tonight's sunset rates a 73/100 (Very Good) with peak viewing at 7:23 PM."
  """

  detailed_analysis: str
  """Hour-by-hour breakdown, weather patterns, and optimal viewing window justification.

  Example:
      The excellent 35km visibility will showcase colors beautifully, while moderate mid-level
      clouds at 40% hit the sweet spot for dramatic enhancement. However, dense low clouds at 60%
      may partially obstruct the horizon view.

      Best strategy: Find an elevated viewing point facing west-southwest to see over the low cloud
      layer. The light precipitation should clear by sunset time, with stable high pressure
      supporting the forecast.

      Photography tip: Use a graduated neutral density filter to balance the bright sky with darker
      foreground elements.

      Confidence: High - all key factors align for a rewarding sunset experience."

      Focus on being the expert interpreter who transforms numbers into vivid, actionable sunset
      guidance.
  """


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

  return agent
