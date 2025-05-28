import operator
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Annotated, Literal, cast

import rich
from langchain_core.runnables import RunnableConfig
from langfuse.callback import CallbackHandler
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.types import RetryPolicy
from langgraph_sdk.schema import Send
from pydantic import AwareDatetime, BaseModel
from pydantic_extra_types.coordinate import Coordinate

from . import APP_DIRS
from .core.date import start_of_local_day
from .core.typing import ensure
from .env import get_postgres_connection_string
from .events.events_api import get_filtered_calendars_with_notes
from .events.model import CalendarsOfInterest, Schedule, end_of_local_day
from .events.prioritizer_agent import RegionalWeatherReports, get_event_prioritizer_agent
from .events.scheduler_agent import get_scheduler_agent
from .location.model import (
  NAMED_LOCATIONS,
  AddressLocation,
  CoordinateLocation,
  Location,
  LocationName,
  NamedLocation,
  ReferencedLocations,
  ResolvedLocation,
  location_named,
)
from .location.resolver_agent import LocationResolverInput, get_location_resolver_agent
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

  briefing_day_location: CoordinateLocation
  """Where Scott and Hilary are at the start of the day.
  TODO: It would be interesting to be able to build multiple briefings if Scott and Hilary are
  apart.
  """

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

  # route_durations_by_event_origin: Mapping[RouteKey, RouteDetailsByMode] | None = None
  # """A dictionary mapping event origin (calendar event ID, coordinate of origin) to
  # route durations. Note that these are not necessary routes that are taken."""

  # weather_analysis: MetereologistOutput

  schedule: Schedule | None = None
  """A schedule of events for the day, including their start and end times, locations, and
  travel information"""


class LocationDataState(BaseModel):
  """A model representing the state of location data in the workflow.
  This model is used to track the status of location data processing and the associated
  coordinates.
  """

  day_start_ts: AwareDatetime
  day_end_ts: AwareDatetime

  event_start_ts: AwareDatetime
  event_end_ts: AwareDatetime

  location: Location
  weather: WeatherReport | None = None


FUTURE_EVENTS_TIMEDELTA = timedelta(days=16)


async def populate_raw_inputs(state: State):
  span_end = state.day_end_ts + FUTURE_EVENTS_TIMEDELTA

  regional_weather = state.regional_weather.model_copy() + await get_weather_report(
    location=state.briefing_day_location,
    report_start_ts=state.day_start_ts,
    report_end_ts=span_end,
    # TODO We should really be getting this data for wherever we'll be in the evening
    include_air_quality=True,
  )

  calendars = CalendarsOfInterest(
    calendars=await get_filtered_calendars_with_notes(
      start_ts=state.day_start_ts,
      end_ts=span_end,
    )
  )

  return {
    "event_consideration_range_end": span_end,
    "calendars": calendars,
    "regional_weather_reports": regional_weather,
  }


async def send_location_requests(state: State) -> Literal["resolve_location"]:
  # Loop over all locations taken from calendars
  # `Send` each of them in turn to resolve_location
  location_data_states = [
    LocationDataState(
      location=AddressLocation(address=ensure(event.location)),
      event_start_ts=event.start_datetime_aware,
      event_end_ts=event.end_datetime_aware,
      day_start_ts=state.day_start_ts,
      day_end_ts=ensure(state.event_consideration_range_end),
    )
    for event in ensure(state.calendars).all_events_with_location()
  ]

  if not location_data_states:
    # If there are no events with locations, we can skip this step
    return []  # type: ignore[return-value]

  return [
    Send(
      node="resolve_location",
      input=state.model_dump(),
    )
    for state in location_data_states
  ]  # type: ignore[return-value]


async def resolve_location(state: LocationDataState) -> LocationDataState:
  if state.location.has_coordinates():
    # If the location already has coordinates, we can skip geocoding
    return state

  location_resolver = get_location_resolver_agent()
  input_location = cast(AddressLocation, state.location)
  input = LocationResolverInput(
    location=input_location,
    home_location=location_named(LocationName.home),
    named_locations=list(NAMED_LOCATIONS.values()),
  )

  result = await location_resolver.run(input)
  if isinstance(result.location, NamedLocation):
    return state
  if isinstance(result.location, CoordinateLocation):
    coordinate = result.location.latlng
    return state.model_copy(
      update={
        "location": ResolvedLocation(
          address=input_location.address,
          latlng=(coordinate.latitude, coordinate.longitude),
        ),
      }
    )

  raise ValueError(result.location.failure_reason or "Unknown location resolution failure")


DISTANCE_WEATHER_THRESHOLD = 40  # km


async def request_weather(state: LocationDataState):
  # At this point, state.location will have a coordinate
  home = location_named(LocationName.home)
  destination = state.location

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
    "referenced_locations": [state.location],
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


async def prioritize_events(state: State) -> State:
  _event_prioritizer = get_event_prioritizer_agent()
  return state


async def write_briefing_outline(state: State) -> State:
  return state


async def write_briefing_script(state: State) -> State:
  return state


builder = StateGraph(State)
builder.add_node(populate_raw_inputs)
builder.add_node(resolve_location)
builder.add_node(request_weather, retry=RetryPolicy(max_attempts=3))
builder.add_node(fork_analysis, defer=True)
builder.add_node(calculate_schedule)
builder.add_node(analyze_weather)
builder.add_node(prioritize_events, defer=True)
builder.add_node(write_briefing_outline)
builder.add_node(write_briefing_script)

builder.set_entry_point("populate_raw_inputs")
builder.add_conditional_edges("populate_raw_inputs", send_location_requests)
builder.add_edge("resolve_location", "request_weather")
builder.add_edge("request_weather", "fork_analysis")
builder.add_edge("populate_raw_inputs", "fork_analysis")
builder.add_conditional_edges("fork_analysis", send_to_analysis_tasks)
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

    rich.print(graph.get_graph().draw_mermaid())
    raise NotImplementedError("Workflow execution is not implemented yet")

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
        saver.list(config=config)
        pass
