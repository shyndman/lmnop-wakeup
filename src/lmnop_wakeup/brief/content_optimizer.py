import re
from datetime import timedelta
from enum import Enum, StrEnum
from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, RootModel, field_validator
from pydantic.dataclasses import dataclass
from pydantic_ai import ModelRetry

from lmnop_wakeup.tools.run_python import run_code

from ..events.model import CalendarEvent
from ..events.prioritizer_agent import PrioritizedEvents
from ..events.scheduler_agent import Schedule
from ..llm import (
  AgentContext,
  LangfuseAgentInput,
  LmnopAgent,
  ModelName,
  RunContext,
  extract_pydantic_ai_callback,
)
from ..weather.model import RegionalWeatherReports
from ..weather.sunset_oracle_agent import SunsetPrediction


class _CalendarEventList(RootModel[list[CalendarEvent]]):
  root: list[CalendarEvent]


class ContentOptimizerInput(LangfuseAgentInput):
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


class TimeBudgetStatus(StrEnum):
  """Overall timing assessment for the briefing content."""

  OPTIMAL = "optimal"  # Content fits well within 2.5-3.5 minute target
  TIGHT = "tight"  # Content pushes upper limit but manageable
  OVER = "over"  # Content exceeds time budget significantly
  UNDER = "under"  # Content falls short, needs more material


class EventCoverage(StrEnum):
  """Depth of coverage recommended for an event."""

  BRIEF_MENTION = "brief_mention"  # 15-25 words, quick reference
  STANDARD_COVERAGE = "standard"  # 30-60 words, normal discussion
  DETAILED_COVERAGE = "detailed"  # 60+ words, in-depth coverage


class ContentType(str, Enum):
  """Type of content being estimated."""

  CALENDAR_EVENT = "calendar_event"
  WEATHER_FORECAST = "weather_forecast"
  TRAVEL_TIMING = "travel_timing"
  CONTEXTUAL_REMARK = "contextual_remark"


@dataclass
class WeatherBriefEstimation:
  """Estimation details for weather forecast coverage."""

  estimated_words: int = Field(
    ...,
    ge=20,  # Weather minimum
    le=100,  # Weather maximum for daily briefing
    description="Estimated word count for weather coverage, based on selected "
    "components (current conditions, today's forecast, weekend preview).",
  )
  coverage_components: list[str] = Field(
    ...,
    description="Which weather components to include: 'current_conditions', "
    "'todays_forecast', 'weekend_preview', 'travel_weather'.",
  )
  rationale: str = Field(
    ..., description="Explanation of weather component selection and word allocation."
  )
  source_data_length: int = Field(
    ..., description="Total word count of available weather data for reference."
  )
  """Estimation details for a single event's briefing coverage."""
  id: str = Field(..., description="The CalendarEvent's unique identifier.")
  summary: str = Field(..., description="Event title/summary from the calendar event.")
  estimated_words: int = Field(
    ...,
    ge=5,  # Minimum realistic word count
    description="Estimated word count for this event's briefing coverage, "
    "accounting for conversational dialogue expansion.",
  )
  coverage_level: EventCoverage = Field(
    ..., description="Recommended depth of coverage for this event."
  )
  rationale: str = Field(
    ...,
    min_length=10,
    description="Detailed explanation for the word allocation and coverage level. "
    "Should explain timing factors, importance, and any special "
    "considerations for this event's inclusion.",
  )
  dialogue_expansion_factor: float = Field(
    default=1.3,
    ge=1.0,
    le=2.0,
    description="Multiplier applied to base content for natural dialogue flow. "
    "Accounts for conversational back-and-forth, transitions, and "
    "character interactions.",
  )


@dataclass
class EventBriefEstimation:
  """Estimation details for a single event's briefing coverage."""

  id: str = Field(..., description="The CalendarEvent's unique identifier.")
  summary: str = Field(..., description="Event title/summary from the calendar event.")
  estimated_words: int = Field(
    ...,
    ge=5,  # Minimum realistic word count
    description="Estimated word count for this event's briefing coverage, "
    "accounting for conversational dialogue expansion.",
  )
  coverage_level: EventCoverage = Field(
    ..., description="Recommended depth of coverage for this event."
  )
  rationale: str = Field(
    ...,
    min_length=10,
    description="Detailed explanation for the word allocation and coverage level. "
    "Should explain timing factors, importance, and any special "
    "considerations for this event's inclusion.",
  )
  content_type: ContentType = Field(
    default=ContentType.CALENDAR_EVENT, description="Type of content this estimation covers."
  )
  dialogue_expansion_factor: float = Field(
    default=1.3,
    ge=1.0,
    le=2.0,
    description="Multiplier applied to base content for natural dialogue flow. "
    "Accounts for conversational back-and-forth, transitions, and "
    "character interactions.",
  )


@dataclass
class SkippedEvent:
  """Details for events excluded from the briefing."""

  id: str = Field(..., description="The CalendarEvent's unique identifier.")
  summary: str = Field(..., description="Event title/summary from the calendar event.")
  skip_reason: str = Field(
    ...,
    description="Primary reason for exclusion (e.g., 'time_constraint', "
    "'low_priority', 'redundant_content', 'scheduling_conflict').",
  )
  rationale: str = Field(
    ...,
    min_length=10,
    description="Detailed explanation for why this event was excluded, "
    "including any timing calculations or priority considerations.",
  )
  rescue_priority: int = Field(
    default=0,
    ge=0,
    le=10,
    description="Priority score (0-10) for including this event if time becomes "
    "available. Higher scores are rescued first.",
  )


class TravelTimingRecommendation(BaseModel):
  """Guidance for including travel timing mentions in the briefing."""

  include_travel_mentions: bool = Field(
    ..., description="Whether travel timing should be mentioned in the briefing."
  )
  rationale: str = Field(
    ..., description="Explanation for travel timing inclusion/exclusion decision."
  )
  estimated_words: int = Field(
    default=0, ge=0, description="Estimated word count if travel mentions are included."
  )


_timedelta_alt_pattern = re.compile(r"^((\d+)h )?(\d+)m (\d+)s")


class ContentOptimizerOutput(BaseModel):
  """Complete analysis and recommendations from the Content Optimizer."""

  # Overall timing assessment
  time_budget_status: TimeBudgetStatus = Field(
    ..., description="Overall assessment of content timing relative to 2.5-3.5 minute target."
  )
  estimated_total_words: int = Field(
    ...,
    ge=200,  # Reasonable minimum for any briefing
    description="Total estimated word count for the complete briefing, including "
    "fixed sections (intro, outro) and variable content.",
  )
  estimated_total_duration: timedelta = Field(
    ...,
    description="Estimated total briefing duration based on 150 words per minute "
    "speaking rate, including natural pauses and transitions. Format should be "
    "HH:MM:SS (e.g., '00:03:00' for 3 minutes).",
  )

  # Weather forecast
  weather_forecast: WeatherBriefEstimation = Field(
    ..., description="Analysis and recommendations for weather forecast coverage."
  )

  # Content recommendations
  must_include: list[EventBriefEstimation] = Field(
    ...,
    description="Events that must be included in the briefing, sourced from "
    "prioritized_events.must_mention. These are non-negotiable.",
  )
  recommended_additions: list[EventBriefEstimation] = Field(
    default_factory=list,
    description="Optional events recommended for inclusion if time permits, "
    "sourced from prioritized_events.could_mention. Ordered by priority.",
  )
  skip_for_time: list[SkippedEvent] = Field(
    default_factory=list,
    description="Events excluded due to time constraints or other factors. "
    "Includes rescue priority for potential inclusion if time allows.",
  )

  # Travel and logistics
  travel_timing: TravelTimingRecommendation = Field(
    ..., description="Recommendations for including travel timing mentions in the briefing."
  )

  # Strategic guidance
  pacing_suggestions: str = Field(
    ...,
    min_length=20,
    description="Strategic guidance for briefing pacing, content groupings, "
    "natural transitions, and handling time pressure. Should provide "
    "actionable advice for the ScriptWriter.",
  )

  # Contingency planning
  running_long_suggestions: str = Field(
    ...,
    min_length=15,
    description="Specific items or strategies to cut first if the briefing runs "
    "over time during delivery. Should be ordered by cut priority.",
  )
  running_short_suggestions: str = Field(
    ...,
    min_length=15,
    description="Specific items or content to add if the briefing runs under time. "
    "May include rescued events or expanded coverage of existing topics.",
  )

  # Analysis metadata
  calculation_confidence: float = Field(
    default=0.8,
    ge=0.0,
    le=1.0,
    description="Confidence score (0.0-1.0) in the timing estimates and "
    "recommendations based on data quality and calculation complexity.",
  )
  optimization_notes: str | None = Field(
    default=None,
    description="Additional notes about the optimization process, edge cases "
    "encountered, or special considerations for this briefing.",
  )

  @field_validator("estimated_total_duration", mode="before")
  @staticmethod
  def parse_timedelta(v):
    if not isinstance(v, str):
      return v
    if m := _timedelta_alt_pattern.match(v):
      hours = int(m.group(2) or 0)
      minutes = int(m.group(3))
      seconds = int(m.group(4))
      return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return v


type ContentOptimizationReport = ContentOptimizerOutput


type ContentOptimizerAgent = LmnopAgent[ContentOptimizerInput, ContentOptimizerOutput]


def get_content_optimizer(config: RunnableConfig) -> ContentOptimizerAgent:
  """Get the content optimizer agent."""

  agent = LmnopAgent[ContentOptimizerInput, ContentOptimizerOutput].create(
    "content_optimizer",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=ContentOptimizerInput,
    output_type=ContentOptimizerOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  @agent.output_validator
  def validate_included_events(
    ctx: RunContext[AgentContext[ContentOptimizerInput]], output: ContentOptimizerOutput
  ) -> ContentOptimizerOutput:
    prioritized_events = ctx.deps.input.prioritized_events

    must_mention_ids = {event.id for event in prioritized_events.must_mention}
    must_include_ids = {event.id for event in output.must_include}
    if any(event.id not in must_include_ids for event in prioritized_events.must_mention):
      raise ModelRetry(
        f"Missing events with the following IDs: {must_mention_ids - must_include_ids}\n"
        "Please incorporate all of the must_mention events",
      )

    return output

  @agent.tool_plain(retries=10)
  def execute_python(code: str, libraries: list[str]) -> str:
    """
     Execute Python code to assist you in your estimation of content length.

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
           - 'math' for mathematical operations (though this is built-in)

     Returns:
       str: The output from the executed code, including any print statements, calculation
             results, error messages, or data summaries. If the code generates plots with
             plotly, the visualization data will be included in the response.

    Note: The execution environment is sandboxed and secure. Code should focus on data
           analysis and calculation rather than system operations or file manipulation.
    """
    return run_code("python", code, libraries=["numpy", "plotly"] + libraries, verbose=True)

  return agent
