# from typing import override

from typing import override

from pydantic import BaseModel, RootModel

from ..llm import LangfuseAgent, LangfuseAgentInput, ModelName
from ..weather.model import RegionalWeatherReports
from .model import CalendarEvent, CalendarEventId, CalendarsOfInterest, Schedule


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


class EventPrioritizerOutput(BaseModel):
  """Output for the event prioritizer agent."""

  must_mention: list[CalendarEventId]
  """
  Events that absolutely need to be included in the briefing:
  - Today's critical wake-up event
  - Today's high-priority events
  - Upcoming personal important events (within reminder window)
  """
  interesting_to_mention: list[CalendarEventId]
  """
  Events worth discussing if space/time allows:
  - Today's standard events
  - Upcoming weekend/weeknight plans (within reminder window)
  - Select informational events that might be particularly relevant
  - Weather conditions for travel destinations or notable local weather patterns
  """
  didnt_quite_make_the_cut: list[CalendarEventId]
  """
  Events that were considered but excluded, with brief reasoning:
  - Informational events that seemed less relevant
  - Events outside optimal reminder windows
  - Events that conflict with higher priorities
  """
  yesterdays_notable: list[CalendarEventId] | None = None
  """
  Interesting observations from yesterday's events for friendly contextual remarks.
  This field is only required if data about the previous day was provided:
  - Personal celebrations (birthdays, anniversaries, etc.)
  - Unusual or irregular events
  - Late-night activities or events ending unusually late
  - Anything that seems worth a casual mention or follow-up
  """


type PrioritizedEvents = EventPrioritizerOutput

type EventPrioritizerAgent = LangfuseAgent[EventPrioritizerInput, EventPrioritizerOutput]


def get_event_prioritizer_agent() -> EventPrioritizerAgent:
  """Get the event prioritizer agent."""

  agent = LangfuseAgent[EventPrioritizerInput, EventPrioritizerOutput].create(
    "event_prioritizer",
    model=ModelName.GEMINI_25_FLASH,
    input_type=EventPrioritizerInput,
    output_type=EventPrioritizerOutput,
  )

  return agent
