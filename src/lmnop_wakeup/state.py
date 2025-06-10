import itertools
import operator
from datetime import timedelta
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, computed_field

from lmnop_wakeup.audio.workflow import TTSState

from .brief.content_optimizer import ContentOptimizationReport
from .brief.model import ConsolidatedBriefingScript
from .brief.script_writer_agent import BriefingScript
from .events.model import CalendarEvent, CalendarsOfInterest, Schedule
from .events.prioritizer_agent import PrioritizedEvents
from .location.model import ReferencedLocations, ResolvedLocation
from .weather.model import RegionalWeatherReports, WeatherKey, WeatherReport
from .weather.sunset_oracle_agent import SunsetPrediction
from .weather.sunset_scoring import SunsetAnalysisResult


class State(BaseModel):
  """A model representing the current state of the workflow's briefing process.
  Contains aggregated data from various sources including calendar entries, locations, and weather
  information necessary for generating a briefing.
  """

  day_start_ts: AwareDatetime
  """Time 0 on the day of the briefing, in the local timezone. This is useful for calculating
  datetime ranges."""

  day_end_ts: AwareDatetime
  """Time -1 (last microsecond) on the day of the briefing, in the local timezone. This is useful
  for calculating datetime ranges."""

  # TODO: It would be interesting to be able to build multiple briefings if Scott and Hilary are
  # apart.
  briefing_day_location: ResolvedLocation
  """Where Scott and Hilary are at the start of the day."""

  event_consideration_range_end: AwareDatetime | None = None
  """The end of the range of events to consider for the briefing."""

  calendars: CalendarsOfInterest | None = None
  """Calendar data containing events, appointments, birthdays, etc"""

  referenced_locations: Annotated[ReferencedLocations, operator.add] = ReferencedLocations()
  """Stores the locations from various sources. Exposes convenience methods for requesting
  lists of sets in various states"""

  regional_weather: Annotated[RegionalWeatherReports, operator.add] = RegionalWeatherReports()
  """Contains weather reports for all locations the user may occupy, for the dates they would
  occupy them, as determined by the calendars"""

  sunset_analysis: SunsetAnalysisResult | None = None
  """Procedurally determined sunset analysis for the day, including cloud cover, air quality,"""

  sunset_prediction: SunsetPrediction | None = None
  """A prediction of the sunset beauty for the day, including the best viewing time and
  overall rating."""

  schedule: Schedule | None = None
  """A schedule of events for the day, including their start and end times, locations, and
  travel information"""

  prioritized_events: PrioritizedEvents | None = None
  """A list of events prioritized for the briefing, including their importance and
  relevance to the day's schedule."""

  content_optimization_report: ContentOptimizationReport | None = None
  """Suggestions for optimizing the briefing content, including events to include and their
  suggested length."""

  briefing_script: BriefingScript | None = None
  """The script for the briefing, including all sections and their content."""

  consolidated_briefing_script: ConsolidatedBriefingScript | None = None
  """The final script for the briefing, with lines grouped into speaker segments for TTS."""

  tts: TTSState | None = None
  """TTS generation state including audio files and master audio."""

  @computed_field
  @property
  def yesterdays_events(self) -> list[CalendarEvent]:
    if self.calendars is None:
      return []

    # Calendars to exclude from yesterday's events based on their notes
    excluded_calendar_ids = {
      "calendar.radarr",  # Movies - noted to never appear in previous day's events
      "calendar.sonarr",  # TV shows - noted to never appear in previous day's events
    }

    return list(
      itertools.chain.from_iterable(
        [
          cal.filter_events_by_range(
            self.day_start_ts - timedelta(days=1), self.day_end_ts - timedelta(days=1)
          )
          for cal in self.calendars.calendars_by_id.values()
          if cal.entity_id not in excluded_calendar_ids
        ]
      )
    )


class LocationDataState(BaseModel):
  """A model representing the state of location data in the workflow.
  This model is used to track the status of location data processing and the associated
  coordinates.
  """

  day_start_ts: AwareDatetime
  day_end_ts: AwareDatetime

  event_start_ts: AwareDatetime
  event_end_ts: AwareDatetime

  address: str
  resolved_location: ResolvedLocation | None = None
  weather: WeatherReport | None = None


class LocationWeatherState(BaseModel):
  """A model representing the state of weather data for a specific location.
  This model is used to track the weather data associated with a resolved location.
  """

  day_start_ts: AwareDatetime
  weather_key: WeatherKey
  reports: list[WeatherReport]
