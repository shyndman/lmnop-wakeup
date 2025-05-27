from contextlib import AsyncExitStack
from datetime import date, timedelta
from typing import cast

import rich
from langchain_core.runnables import RunnableConfig
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.types import RetryPolicy
from langgraph_sdk.schema import Send
from pydantic import AwareDatetime, BaseModel

from lmnop_wakeup.core.typing import ensure
from lmnop_wakeup.events.prioritizer import get_event_prioritizer_agent
from lmnop_wakeup.location.resolver_agent import LocationResolverInput
from lmnop_wakeup.location.routes_api import (
  ArriveByConstraint,
  DepartAtConstraint,
  compute_route_durations,
)
from lmnop_wakeup.schedule.scheduler import get_scheduler_agent

from . import APP_DIRS
from .core.date import start_of_local_day
from .env import get_postgres_connection_string
from .events.events_api import get_filtered_calendars_with_notes
from .events.model import CalendarsOfInterest, end_of_local_day
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
from .location.resolver_agent import get_location_resolver_agent
from .weather.model import RegionalWeatherReports, WeatherReport
from .weather.weather_api import get_weather_report


class State(BaseModel):
  """A model representing the current state of the workflow's briefing process.
  Contains aggregated data from various sources including calendar entries, locations, and weather
  information necessary for generating a briefing.
  """

  day_start_ts: AwareDatetime
  """Time 0 on the day of the briefing, in the local timezone. This is useful for calculating
  datetime ranges."""
  day_end_ts: AwareDatetime
  """Time -1 on the day of the briefing, in the local timezone. This is useful for calculating
  datetime ranges."""
  briefing_day_location: Location
  """Where Scott and Hilary are at the start of the day.

  TODO: It would be interesting to be able to build multiple briefings if Scott and Hilary are
  apart."""
  event_consideration_range_end: AwareDatetime | None = None
  """The end of the range of events to consider for the briefing."""
  calendars: CalendarsOfInterest | None = None
  """Calendar data containing events, appointments, birthdays, etc"""
  referenced_locations: ReferencedLocations | None = None
  """Stores the locations from various sources. Exposes convenience methods for requesting
  lists of sets in various states"""
  weather: RegionalWeatherReports | None = None
  """Contains weather reports for all locations the user may occupy, for the dates they would
  occupy them, as determined by the calendars"""
  route_durations_by_time: dict[str, float] | None = None
  # schedule: Schedule


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


FUTURE_EVENTS_TIMEDELTA = timedelta(days=21)


async def populate_raw_inputs(state: State):
  span_end = state.day_end_ts + FUTURE_EVENTS_TIMEDELTA
  return {
    "calendars": CalendarsOfInterest(
      calendars=await get_filtered_calendars_with_notes(
        start_ts=state.day_start_ts, end_ts=span_end
      )
    ),
    "event_consideration_range_end": span_end,
  }


async def send_location_requests(state: State):
  # Loop over all locations taken from calendars
  # `Send` each of them in turn to resolve_location
  return [
    Send(node="resolve_location", input=state.model_dump())
    for state in [
      *(
        LocationDataState(
          location=AddressLocation(address=ensure(event.location)),
          event_start_ts=event.start_datetime_aware,
          event_end_ts=event.end_datetime_aware,
          day_start_ts=state.day_start_ts,
          day_end_ts=ensure(state.event_consideration_range_end),
        )
        for event in ensure(state.calendars).all_events_with_location()
      ),
    ]
  ]


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
    weather_report = await get_weather_report(
      destination, state.event_start_ts - timedelta(hours=1), state.event_end_ts
    )
    state.weather = weather_report.trim_to_datetime(state.event_end_ts + timedelta(hours=1))

  return state


async def calculate_briefing_day_routes(state: LocationDataState):
  if state.event_end_ts < state.day_start_ts or state.event_start_ts > state.day_end_ts:
    # If the event is outside the day range, we can skip it
    return state

  if not isinstance(state.location, CoordinateLocation):
    return state

  distance = location_named(LocationName.home).distance_to(state.location)

  if distance > DISTANCE_WEATHER_THRESHOLD:
    state.weather = await get_weather_report(
      state.location, state.event_start_ts, state.event_end_ts
    )

  home = location_named(LocationName.home)
  outgoing_route_durations = await compute_route_durations(
    origin=home,
    destination=state.location,
    time_constraint=ArriveByConstraint(time=state.day_start_ts),
    include_walking=True,
    include_cycling=True,
    include_transit=True,
  )
  incoming_route_durations = await compute_route_durations(
    origin=home,
    destination=state.location,
    time_constraint=DepartAtConstraint(time=state.day_start_ts),
    include_walking=outgoing_route_durations.walk is not None,
    include_cycling=outgoing_route_durations.bike is not None,
    include_transit=outgoing_route_durations.transit is not None,
  )

  return {
    "route_durations": [outgoing_route_durations, incoming_route_durations],
  }


async def calculate_schedule(state: State) -> State:
  _scheduler = get_scheduler_agent()
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
builder.add_node(calculate_briefing_day_routes, retry=RetryPolicy(max_attempts=3))
builder.add_node(calculate_schedule, defer=True)
builder.add_node(prioritize_events)
builder.add_node(write_briefing_outline)
builder.add_node(write_briefing_script)
builder.set_entry_point("populate_raw_inputs")
builder.add_conditional_edges("populate_raw_inputs", send_location_requests)
builder.add_edge("resolve_location", "request_weather")
builder.add_edge("request_weather", "calculate_routes")
builder.add_edge("calculate_routes", "calculate_schedule")
builder.add_edge("calculate_schedule", "prioritize_events")
builder.add_edge("prioritize_events", "write_briefing_outline")
builder.add_edge("write_briefing_outline", "write_briefing_script")
builder.set_finish_point("write_briefing_script")


async def run_briefing_workflow(briefing_date: date) -> None:
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
    config: RunnableConfig = {"configurable": {"thread_id": briefing_date.isoformat()}}

    day_start_ts = start_of_local_day(briefing_date)
    for _ in range(3):
      # Run the workflow with a state update
      rich.print(
        await graph.ainvoke(
          input=State(
            day_start_ts=day_start_ts,
            day_end_ts=end_of_local_day(day_start_ts),
            briefing_day_location=location_named(LocationName.home),
          ),
          config=config,
          stream_mode="updates",
        )
      )

  # Run the workflow
  # await workflow.run(briefing_date)
