# from typing import override

from typing import override

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, RootModel
from pydantic.dataclasses import dataclass

from ..llm import LangfuseAgentInput, LmnopAgent, ModelName, extract_pydantic_ai_callback
from ..weather.model import RegionalWeatherReports
from .model import CalendarEvent, CalendarsOfInterest, Schedule


class _CalendarEventList(RootModel[list[CalendarEvent]]):
  root: list[CalendarEvent]


class EventPrioritizerInput(LangfuseAgentInput):
  """Input for the event prioritizer agent."""

  schedule: Schedule
  calendars_of_interest: CalendarsOfInterest
  regional_weather_reports: RegionalWeatherReports
  yesterdays_events: list[CalendarEvent] | None

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      "schedule": self.schedule.model_dump_json(),
      "calendars_of_interest": self.calendars_of_interest.model_dump_markdown(),
      "regional_weather_reports": self.regional_weather_reports.model_dump_json(
        exclude={"reports_by_location"}
      ),
      "yesterdays_events": _CalendarEventList(self.yesterdays_events).model_dump_json(indent=2)
      if self.yesterdays_events
      else "[]",
    }


@dataclass
class PrioritizedEvent:
  """Represents a prioritized event with its ID and reason for prioritization."""

  id: str
  """The CalendarEvent's id field """

  summary: str
  """The CalendarEvent's summary field"""

  reason: str
  """
  Reason for prioritization:
  - Wake-up events
  - Prioritized events
  - Upcoming personal events (within reminder window)
  - Interesting or relevant events worth mentioning
  - Weather conditions affecting travel or local patterns
  """
  tag: str
  """Categorization/prioritization tag"""


class EventPrioritizerOutput(BaseModel):
  """Output for the event prioritizer agent."""

  must_mention: list[PrioritizedEvent]
  """
  Events that absolutely need to be included in the briefing:
  - Today's wake-up event
  - Today's prioritized events
  - Upcoming personal events (within reminder window)
  """

  could_mention: list[PrioritizedEvent]
  """
  Events that might be worth discussing, in descending order of priority:
  - Today's standard events
  - Upcoming weekend/weeknight plans (within reminder window)
  - Select informational events that might be particularly relevant
  - Weather conditions for travel destinations or notable local weather patterns
  - Upcoming media, particularly if there's a signal that the user enjoys the show/genre/director
    etc. But keep it fresh, and don't repeat yourself day after day. You should only mention the
    media once as it's coming up, and definitely prioritize mentioning on the day it comes out (if
    the users like it). (we'll provide details of the media mentioned on previous days for
    cross-checking)
  - Nearby community events. Use similar rules to upcoming media, with the added consideration of
    distance.
  """

  deprioritized: list[PrioritizedEvent]
  """
  Events that were considered but excluded, with brief reasoning:
  - Events outside optimal reminder windows
  - Events that conflict with higher priorities
  """

  last_nights_notable: list[PrioritizedEvent] | None = None
  """
  Interesting observations from last night's events, if any, for friendly contextual remarks.
  This field is only required if data about the previous night was provided:
  - Personal celebrations (birthdays, anniversaries, etc.)
  - Unusual or irregular events
  - Late-night activities or events ending unusually late
  """


type PrioritizedEvents = EventPrioritizerOutput

type EventPrioritizerAgent = LmnopAgent[EventPrioritizerInput, EventPrioritizerOutput]


def get_event_prioritizer_agent(config: RunnableConfig) -> EventPrioritizerAgent:
  """Get the event prioritizer agent."""

  agent = LmnopAgent[EventPrioritizerInput, EventPrioritizerOutput].create(
    "event_prioritizer",
    model_name=ModelName.GEMINI_25_FLASH,
    input_type=EventPrioritizerInput,
    output_type=EventPrioritizerOutput,
    callback=extract_pydantic_ai_callback(config),
  )

  return agent
