# from typing import override

from pydantic import BaseModel

from lmnop_wakeup.events.model import CalendarEvent, CalendarsOfInterest

from ..llm import LangfuseAgent, LangfuseInput, ModelName
from ..schedule.scheduler import SchedulerOutput
from ..weather.model import RegionalWeatherReports


class EventPrioritizerInput(LangfuseInput):
  """Input for the location resolver agent."""

  schedule: SchedulerOutput
  calendars: CalendarsOfInterest
  # current_date_info
  weather_data: RegionalWeatherReports
  yesterday_events: list[CalendarEvent]

  # @override
  # def to_prompt_variable_map(self) -> dict[str, str]:
  #   """Convert the input to a map of prompt variables."""
  #   return {
  #     "schedule": self.schedule,
  #     "calendars": self.calendars,
  #     "current_date_info": self.current_date_info,
  #     "weather_data": self.weather_data,
  #     "yesterday_events": self.yesterday_events,
  #   }


class EventPrioritizerOutput(BaseModel):
  """Output for the location resolver agent."""

  """Set to the NamedLocation, if the input location was identified as one of the user's named
  locations, or a CoordinateLocation returned by the geocode tool.

  If no location could be determined, set this value to a ResolutionFailure instance, describing
  the problem."""


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
