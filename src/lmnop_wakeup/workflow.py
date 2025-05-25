from contextlib import AsyncExitStack
from datetime import date, timedelta
from typing import cast

import rich
from langchain_core.runnables import RunnableConfig
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph_sdk.schema import Send
from pydantic import AwareDatetime, BaseModel

from . import APP_DIRS
from .core.date import start_of_local_day
from .core.typing import nn
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
from .location.resolver_agent import LocationResolverInput, get_location_resolver_agent
from .weather.model import RegionalWeatherReports, WeatherReport


class State(BaseModel):
  """A model representing the current state of the workflow's briefing process.
  Contains aggregated data from various sources including calendar entries, locations, and weather
  information necessary for generating a briefing.
  """

  briefing_day_start: AwareDatetime
  """Time 0 on the day of the briefing, in the local timezone. This is useful for calculating
  datetime ranges."""
  briefing_day_location: Location
  """Where Scott and Hilary are at the start of the day.

  TODO: It would be interesting to be able to build multiple briefings if Scott and Hilary are
  apart."""
  event_consideration_range_end: AwareDatetime | None = None
  calendars: CalendarsOfInterest | None = None
  """Calendar data containing events, appointments, birthdays, etc"""
  referenced_locations: ReferencedLocations | None = None
  """Stores the locations from various sources. Exposes convenience methods for requesting
  lists of sets in various states"""
  weather: RegionalWeatherReports | None = None
  """Contains weather reports for all locations the user may occupy, for the dates they would
  occupy them, as determined by the calendars"""
  # schedule: Schedule


async def write_briefing_script(state: State) -> State:
  return state


async def write_briefing_outline(state: State) -> State:
  return state


async def prioritize_events(state: State) -> State:
  return state


async def calculate_schedule(state: State) -> State:
  return state


# tools:
# - weather summary (from: datetime, to): str


class LocationDataState(BaseModel):
  """A model representing the state of location data in the workflow.
  This model is used to track the status of location data processing and the associated
  coordinates.
  """

  location: Location
  start_ts: AwareDatetime
  end_ts: AwareDatetime
  weather: WeatherReport | None = None


async def request_weather(state: State) -> State:
  # At this point, state.location will have a coordinate

  return state


async def resolve_location(state: LocationDataState) -> LocationDataState:
  if state.location.has_coordinates():
    # If the location already has coordinates, we can skip geocoding
    return state

  agent = get_location_resolver_agent()
  input_location = cast(AddressLocation, state.location)
  input = LocationResolverInput(
    location=input_location,
    home_location=location_named(LocationName.home),
    named_locations=list(NAMED_LOCATIONS.values()),
  )

  result = await agent.run(input)
  if isinstance(result.location, NamedLocation):
    return state
  if isinstance(result.location, CoordinateLocation):
    return state.model_copy(
      update={
        "location": ResolvedLocation(
          address=input_location.address,
          latlng=result.location.latlng,
        ),
      }
    )

  raise ValueError(result.failure_reason)


async def send_location_requests(state: State):
  # Loop over all locations taken from calendars
  # `Send` each of them in turn to resolve_location
  return [
    Send(node="resolve_location", input=state.model_dump())
    for state in [
      # NAMED LOCATIONS
      *(
        LocationDataState(
          location=location,
          start_ts=state.briefing_day_start,
          end_ts=nn(state.event_consideration_range_end),
        )
        for location in NAMED_LOCATIONS.values()
      ),
      # EVENT LOCATIONS
      *(
        LocationDataState(
          location=AddressLocation(address=nn(event.location)),
          start_ts=event.start_datetime_aware,
          end_ts=event.end_datetime_aware,
        )
        for event in nn(state.calendars).all_events_with_location()
      ),
    ]
  ]


FUTURE_EVENTS_TIMEDELTA = timedelta(days=21)


async def populate_raw_inputs(state: State):
  day_start = state.briefing_day_start
  day_end = end_of_local_day(state.briefing_day_start)
  span_end = day_end + FUTURE_EVENTS_TIMEDELTA
  return {
    "calendars": CalendarsOfInterest(
      calendars=await get_filtered_calendars_with_notes(start_ts=day_start, end_ts=span_end)
    ),
    "event_consideration_range_end": span_end,
  }


builder = StateGraph(State)
builder.add_node(populate_raw_inputs)
builder.add_node(resolve_location)
builder.add_node(request_weather)
builder.add_node(calculate_schedule)
builder.add_node(prioritize_events)
builder.add_node(write_briefing_outline)
builder.add_node(write_briefing_script)
builder.set_entry_point("populate_raw_inputs")
builder.add_conditional_edges("populate_raw_inputs", send_location_requests)
builder.add_edge("resolve_location", "request_weather")
builder.add_edge("request_weather", "calculate_schedule")
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

    start_of_briefing_day = start_of_local_day(briefing_date)
    for _ in range(3):
      # Run the workflow with a state update
      rich.print(
        await graph.ainvoke(
          input=State(
            briefing_day_start=start_of_briefing_day,
            briefing_day_location=location_named(LocationName.home),
          ),
          config=config,
          stream_mode="updates",
        )
      )

  # Run the workflow
  # await workflow.run(briefing_date)
