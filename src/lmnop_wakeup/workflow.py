import itertools
import operator
from collections.abc import Mapping
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated, Literal, cast

import rich
from langchain_core.runnables import RunnableConfig
from langfuse.callback import CallbackHandler
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.types import CachePolicy, RetryPolicy, Send
from pydantic import AwareDatetime, BaseModel, computed_field
from pydantic_extra_types.coordinate import Coordinate

from . import APP_DIRS
from .brief.model import BriefingScript, CharacterPool
from .brief.script_writer_agent import ScriptWriterInput, get_script_writer_agent
from .brief.sectioner_agent import BriefingOutline, SectionerInput, get_sectioner_agent
from .core.date import start_of_local_day
from .core.typing import assert_not_none, ensure
from .env import get_postgres_connection_string
from .events.events_api import get_filtered_calendars_with_notes
from .events.model import CalendarEvent, CalendarsOfInterest, Schedule, end_of_local_day
from .events.prioritizer_agent import (
  PrioritizedEvents,
  RegionalWeatherReports,
  get_event_prioritizer_agent,
)
from .events.scheduler_agent import RouteDetailsByMode, get_scheduler_agent
from .location.model import (
  NAMED_LOCATIONS,
  CoordinateLocation,
  LocationName,
  ReferencedLocations,
  ResolvedLocation,
  location_named,
)
from .location.resolver_agent import LocationResolverInput, get_location_resolver_agent
from .weather.meteorologist_agent import WeatherReportForBrief
from .weather.sunset_oracle_agent import SunsetPrediction
from .weather.weather_api import WeatherReport, get_weather_report

type RouteKey = tuple[str, Coordinate]


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
  briefing_day_location: CoordinateLocation
  """Where Scott and Hilary are at the start of the day."""

  event_consideration_range_end: AwareDatetime | None = None
  """The end of the range of events to consider for the briefing."""

  calendars: CalendarsOfInterest | None = None
  """Calendar data containing events, appointments, birthdays, etc"""

  referenced_locations: Annotated[ReferencedLocations, operator.add] | None = None
  """Stores the locations from various sources. Exposes convenience methods for requesting
  lists of sets in various states"""

  regional_weather: Annotated[RegionalWeatherReports, operator.add] = RegionalWeatherReports()
  """Contains weather reports for all locations the user may occupy, for the dates they would
  occupy them, as determined by the calendars"""

  route_durations: Mapping[RouteKey, RouteDetailsByMode] | None = None
  """A dictionary mapping event origin (calendar event ID, coordinate of origin) to
  route durations. Note that these are not necessary routes that are taken."""

  sunset_prediction: SunsetPrediction | None = None
  """A prediction of the sunset beauty for the day, including the best viewing time and
  overall rating."""

  weather_analysis: WeatherReportForBrief | None = None
  """A weather report for the day, including temperature, conditions, and air quality."""

  schedule: Schedule | None = None
  """A schedule of events for the day, including their start and end times, locations, and
  travel information"""

  prioritized_events: PrioritizedEvents | None = None
  """A list of events prioritized for the briefing, including their importance and
  relevance to the day's schedule."""

  briefing_outline: BriefingOutline | None = None
  """An outline of the briefing, including sections and their content."""

  briefing_script: BriefingScript | None = None
  """The final script for the briefing, including all sections and their content."""

  @computed_field
  @property
  def yesterday_events(self) -> list[CalendarEvent]:
    if self.calendars is None:
      return []

    return list(
      itertools.chain.from_iterable(
        [
          cal.filter_events_by_range(
            self.day_start_ts - timedelta(days=1), self.day_end_ts - timedelta(days=1)
          )
          for cal in self.calendars.calendars_by_id.values()
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
  resolved_location: CoordinateLocation | None = None
  weather: WeatherReport | None = None


FUTURE_EVENTS_TIMEDELTA = timedelta(days=16)


async def populate_raw_inputs(state: State):
  span_end = state.day_end_ts + FUTURE_EVENTS_TIMEDELTA

  local_weather = await get_weather_report(
    location=state.briefing_day_location,
    report_start_ts=state.day_start_ts,
    report_end_ts=span_end,
    # TODO We should really be getting this data for wherever we'll be in the evening
    include_air_quality=True,
  )

  calendars = CalendarsOfInterest(
    calendars=await get_filtered_calendars_with_notes(
      start_ts=cast(datetime, state.day_start_ts) - timedelta(days=1),
      end_ts=span_end,
    )
  )

  regional_weather = RegionalWeatherReports(
    reports_by_latlng={
      state.briefing_day_location.latlng: [local_weather],
    }
  )

  return {
    "event_consideration_range_end": span_end,
    "calendars": calendars,
    "regional_weather_reports": regional_weather,
  }


async def send_location_requests(state: State) -> Literal["resolve_location"]:
  # import debugpy

  # logger.debug("Beginning debugpy session")
  # debugpy.listen(("0.0.0.0", 5678))
  # debugpy.wait_for_client()

  # Loop over all locations taken from calendars
  # `Send` each of them in turn to resolve_location
  location_data_states = [
    LocationDataState(
      address=event.location,
      event_start_ts=event.start_datetime_aware,
      event_end_ts=event.end_datetime_aware,
      day_start_ts=state.day_start_ts,
      day_end_ts=ensure(state.event_consideration_range_end),
    )
    for event in ensure(state.calendars).all_events_with_location()
    if event.location is not None and event.location.strip() != ""
  ]

  if not location_data_states:
    # If there are no events with locations, we can skip this step
    return []  # type: ignore[return-value]

  return [
    Send(
      "resolve_location",
      loc_state,
    )
    for loc_state in location_data_states
  ]  # type: ignore[return-value]


async def resolve_location(state: LocationDataState) -> LocationDataState:
  location_resolver = get_location_resolver_agent()
  input = LocationResolverInput(
    address=state.address,
    home_location=location_named(LocationName.home),
    named_locations=list(NAMED_LOCATIONS.values()),
  )

  result = await location_resolver.run(input)

  if result.special_location is not None:
    if result.special_location not in LocationName:
      raise ValueError(f"Special location {result.special_location} is not a valid LocationName")
    return state.model_copy(
      update={
        "resolved_location": location_named(LocationName(result.special_location)),
      }
    )

  if isinstance(result.geocoded_location, ResolvedLocation):
    return state.model_copy(
      update={
        "resolved_location": result.geocoded_location,
      }
    )

  raise ValueError(result.failure_reason or "Unknown location resolution failure")


DISTANCE_WEATHER_THRESHOLD = 40  # km


async def request_weather(state: LocationDataState):
  # At this point, state.location will have a coordinate
  home = location_named(LocationName.home)
  destination = state.resolved_location

  if (
    isinstance(destination, CoordinateLocation)
    and home.distance_to(destination) > DISTANCE_WEATHER_THRESHOLD
  ):
    state.weather = await get_weather_report(
      location=destination,
      report_start_ts=state.event_start_ts - timedelta(hours=1),
      report_end_ts=state.event_end_ts + timedelta(hours=1),
      include_air_quality=False,
    )

  return {
    "regional_weather": [state.weather],
    "referenced_locations": [state.resolved_location],
  }


async def fork_analysis(state: State) -> State:
  """This node exists to fork via a conditional edge, and nothing else"""
  raise Exception("Under construction")
  return state


async def send_to_analysis_tasks(
  state: State,
) -> list[Literal["calculate_schedule", "analyze_weather", "predict_sunset_beauty"]]:
  return ["calculate_schedule", "analyze_weather", "predict_sunset_beauty"]


async def calculate_schedule(state: State) -> State:
  _scheduler = get_scheduler_agent()
  return state


async def analyze_weather(state: State) -> State:
  # TODO This won't realistically work for non-home locations, but I'm going to be
  # adding support shortly.

  # state.weather = weather_report.trim_to_datetime(state.day_end_ts + timedelta(hours=1))
  return state


async def predict_sunset_beauty(state: State) -> State:
  return state


async def prioritize_events(state: State) -> State:
  _event_prioritizer = get_event_prioritizer_agent()
  return state


async def write_briefing_outline(state: State) -> State:
  sectioner = get_sectioner_agent()
  input = SectionerInput(
    schedule=assert_not_none(state.schedule),
    prioritized_events=assert_not_none(state.prioritized_events),
    regional_weather_reports=assert_not_none(state.regional_weather),
    yesterday_events=assert_not_none(state.yesterday_events),
  )
  out = await sectioner.run(input=input)
  state.model_copy(update={"briefing_script": out})
  return state.model_copy(update={"briefing_script": out})


async def write_briefing_script(state: State) -> State:
  script_writer = get_script_writer_agent()
  input = ScriptWriterInput(
    briefing_outline=assert_not_none(state.briefing_outline),
    prioritized_events=assert_not_none(state.prioritized_events),
    schedule=assert_not_none(state.schedule),
    weather_report=assert_not_none(state.weather_analysis),
    sunset_prediction=assert_not_none(state.sunset_prediction),
    character_pool=CharacterPool(),
    previous_scripts=[],
  )
  out = await script_writer.run(input=input)
  state.model_copy(update={"briefing_script": out})
  return state.model_copy(update={"briefing_script": out})


builder = StateGraph(State)
builder.add_node(populate_raw_inputs, cache_policy=CachePolicy(ttl=120 * 60))
builder.add_node(resolve_location)
builder.add_node(request_weather, retry=RetryPolicy(max_attempts=3))
builder.add_node(fork_analysis, defer=True)
builder.add_node(calculate_schedule)
builder.add_node(analyze_weather)
builder.add_node(predict_sunset_beauty)
builder.add_node(prioritize_events, defer=True)
builder.add_node(write_briefing_outline)
builder.add_node(write_briefing_script)

builder.set_entry_point("populate_raw_inputs")
builder.add_conditional_edges(
  "populate_raw_inputs", send_location_requests, then="resolve_location"
)
builder.add_edge("resolve_location", "request_weather")
builder.add_edge("request_weather", "fork_analysis")
builder.add_edge("populate_raw_inputs", "fork_analysis")
builder.add_conditional_edges(
  "fork_analysis",
  send_to_analysis_tasks,
  {
    "calculate_schedule": "calculate_schedule",
    "analyze_weather": "analyze_weather",
    "predict_sunset_beauty": "predict_sunset_beauty",
  },
)
builder.add_edge("calculate_schedule", "prioritize_events")
builder.add_edge("analyze_weather", "prioritize_events")
builder.add_edge("predict_sunset_beauty", "prioritize_events")
builder.add_edge("prioritize_events", "write_briefing_outline")
builder.add_edge("write_briefing_outline", "write_briefing_script")
builder.set_finish_point("write_briefing_script")


@dataclass
class Run:
  briefing_date: date
  briefing_location: CoordinateLocation


@dataclass
class ListCheckpoints:
  briefing_date: date


type WorkflowCommand = Run | ListCheckpoints


def config_for_date(briefing_date: date) -> RunnableConfig:
  """Create a configuration for the workflow based on the briefing date."""
  return {
    "configurable": {
      "thread_id": briefing_date.isoformat(),
      # "checkpoint_id": "1f03c061-e828-6d6b-8009-f87baade1033",
    }
  }


async def run_workflow_command(cmd: WorkflowCommand) -> None:
  """Run the morning briefing workflow.

  Args:
      briefing_date: The date for which to run the briefing.
  """

  pg_connection_string = get_postgres_connection_string()
  async with AsyncExitStack() as stack:
    store = await stack.enter_async_context(
      AsyncPostgresStore.from_conn_string(pg_connection_string)
    )
    await store.setup()
    saver = await stack.enter_async_context(
      AsyncPostgresSaver.from_conn_string(pg_connection_string)
    )
    await saver.setup()

    graph = builder.compile(
      cache=SqliteCache(path=str(APP_DIRS.user_cache_path / "cache.db")),
      checkpointer=saver,
      store=store,
    )

    # rich.print(graph.get_graph().draw_mermaid())
    # raise NotImplementedError("Workflow execution is not implemented yet")

    match cmd:
      case Run(briefing_date, location):
        config: RunnableConfig = config_for_date(briefing_date)
        config["callbacks"] = [CallbackHandler()]
        day_start_ts = start_of_local_day(briefing_date)
        # Run the workflow with a state update
        rich.print(
          await graph.ainvoke(
            input=State(
              day_start_ts=day_start_ts,
              day_end_ts=end_of_local_day(day_start_ts),
              briefing_day_location=location,
            ),
            config=config,
            stream_mode="updates",
          )
        )

      case ListCheckpoints(briefing_date):
        config = config_for_date(briefing_date)
        async for checkpoint in saver.alist(config=config):
          print(checkpoint.config)
