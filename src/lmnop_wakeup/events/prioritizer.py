# from typing import override

from typing import override

from pydantic import BaseModel

from ..events.model import CalendarEvent, CalendarEventId, CalendarsOfInterest
from ..llm import LangfuseAgent, LangfuseInput, ModelName
from ..schedule.scheduler import SchedulerOutput
from ..weather.model import RegionalWeatherReports


class EventPrioritizerInput(LangfuseInput):
  """Input for the location resolver agent."""

  schedule: SchedulerOutput
  calendars_of_interest: CalendarsOfInterest
  regional_weather_reports: RegionalWeatherReports
  yesterday_events: list[CalendarEvent] | None

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    """Convert the input to a map of prompt variables."""
    return {
      k: v.model_dump_json() if v is not None else "null"
      for k, v in {
        "schedule": self.schedule,
        "calendars_of_interest": self.calendars_of_interest,
        "regional_weather_reports": self.regional_weather_reports,
        "yesterday_events": self.yesterday_events,
      }.items()
    }


class EventPrioritizerOutput(BaseModel):
  """Output for the location resolver agent."""

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


type EventPrioritizerAgent = LangfuseAgent[EventPrioritizerInput, EventPrioritizerOutput]


def get_event_prioritizer_agent() -> EventPrioritizerAgent:
  """Get the location resolver agent."""

  agent = LangfuseAgent[EventPrioritizerInput, EventPrioritizerOutput].create(
    "event_prioritizer",
    model=ModelName.GEMINI_25_FLASH,
    input_type=EventPrioritizerInput,
    output_type=EventPrioritizerOutput,
  )

  return agent
