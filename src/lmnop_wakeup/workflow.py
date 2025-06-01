import asyncio
import itertools
import operator
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal, cast

import rich
from langchain_core.runnables import RunnableConfig
from langfuse.callback import CallbackHandler
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.types import CachePolicy, RetryPolicy, Send
from pydantic import AwareDatetime, BaseModel, computed_field
from pydantic_extra_types.coordinate import Coordinate

from lmnop_wakeup.weather.model import WeatherKey, weather_key_for_location

from . import APP_DIRS
from .brief.actors import CHARACTER_POOL
from .brief.script_writer_agent import BriefingScript, ScriptWriterInput, get_script_writer_agent
from .brief.sectioner_agent import BriefingOutline, SectionerInput, get_sectioner_agent
from .core.date import start_of_local_day
from .core.tracing import langfuse_span, trace
from .core.typing import assert_not_none, ensure
from .env import get_postgres_connection_string
from .events.events_api import get_filtered_calendars_with_notes
from .events.model import CalendarEvent, CalendarsOfInterest, Schedule, end_of_local_day
from .events.prioritizer_agent import (
  EventPrioritizerInput,
  PrioritizedEvents,
  RegionalWeatherReports,
  get_event_prioritizer_agent,
)
from .events.scheduler_agent import SchedulerInput, get_scheduler_agent
from .location.model import (
  NAMED_LOCATIONS,
  CoordinateLocation,
  LocationName,
  NamedLocation,
  ReferencedLocations,
  ResolvedLocation,
  location_named,
)
from .location.resolver_agent import LocationResolverInput, get_location_resolver_agent
from .weather.meteorologist_agent import (
  MeteorologistInput,
  get_meteorologist_agent,
)
from .weather.sunset_oracle_agent import (
  SunsetOracleInput,
  SunsetPrediction,
  get_sunset_oracle_agent,
)
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

  sunset_prediction: SunsetPrediction | None = None
  """A prediction of the sunset beauty for the day, including the best viewing time and
  overall rating."""

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
  def yesterdays_events(self) -> list[CalendarEvent]:
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
  resolved_location: ResolvedLocation | None = None
  weather: WeatherReport | None = None


class LocationWeatherState(BaseModel):
  """A model representing the state of weather data for a specific location.
  This model is used to track the weather data associated with a resolved location.
  """

  day_start_ts: AwareDatetime
  weather_key: WeatherKey
  reports: list[WeatherReport]


FUTURE_EVENTS_TIMEDELTA = timedelta(days=15)


@trace()
async def populate_raw_inputs(state: State):
  span_end = state.day_end_ts + FUTURE_EVENTS_TIMEDELTA

  local_weather = await get_weather_report(
    location=state.briefing_day_location,
    report_start_ts=state.day_start_ts,
    report_end_ts=span_end,
    # TODO We should really be getting this data for wherever we'll be in the evening
    include_air_quality=True,
    include_comfort_hourly=True,
  )

  calendars = CalendarsOfInterest(
    calendars_by_id={
      calendar.entity_id: calendar
      for calendar in await get_filtered_calendars_with_notes(
        briefing_date=cast(datetime, state.day_start_ts),
        start_ts=cast(datetime, state.day_start_ts) - timedelta(days=1),
        end_ts=span_end,
      )
    }
  )

  location = state.briefing_day_location
  key = weather_key_for_location(location)
  regional_weather = RegionalWeatherReports(
    reports_by_location={
      key: [local_weather],  # type: ignore
    }
  )

  return {
    "event_consideration_range_end": span_end,
    "calendars": calendars,
    "regional_weather": regional_weather,
  }


@trace()
async def send_location_requests(state: State):
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
      "process_location",
      loc_state,
    )
    for loc_state in location_data_states
  ]  # type: ignore[return-value]


@trace()
async def process_location(new_state: LocationDataState):
  loc_state = LocationDataState.model_validate(
    cast(
      dict,
      await location_graph.ainvoke(new_state),
    )
  )

  state_delta: dict[str, Any] = {}

  if not isinstance(loc_state.resolved_location, NamedLocation):
    state_delta["referenced_locations"] = ReferencedLocations(
      adhoc_location_map={
        assert_not_none(loc_state.resolved_location).address: assert_not_none(
          loc_state.resolved_location
        )
      }
    )

  weather = loc_state.weather
  loc = loc_state.resolved_location
  if weather is not None and loc is not None:
    state_delta["regional_weather"] = RegionalWeatherReports(
      reports_by_location={loc: [weather]}  # type: ignore
    )

  return state_delta


@trace()
async def resolve_location(state: LocationDataState):
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
    return {
      "resolved_location": location_named(LocationName(result.special_location)),
    }

  if isinstance(result.geocoded_location, ResolvedLocation):
    return {
      "resolved_location": result.geocoded_location,
    }

  raise ValueError(result.failure_reason or "Unknown location resolution failure")


DISTANCE_WEATHER_THRESHOLD = 40  # km


@trace()
async def request_weather(state: LocationDataState):
  # At this point, state.location will have a coordinate
  home = location_named(LocationName.home)
  destination = state.resolved_location

  if (
    isinstance(destination, CoordinateLocation)
    and home.distance_to(destination) > DISTANCE_WEATHER_THRESHOLD
  ):
    return {
      "weather": await get_weather_report(
        location=destination,
        report_start_ts=state.event_start_ts - timedelta(hours=2),
        report_end_ts=state.event_end_ts + timedelta(hours=2),
        include_air_quality=False,
      )
    }

  return {}


@trace()
async def fork_analysis(state: State):
  """This node exists to fork via conditional edges, and nothing else"""
  return {}


@trace()
async def send_to_analysis_tasks(
  state: State,
) -> list[Literal["calculate_schedule", "analyze_weather", "predict_sunset_beauty"]]:
  return ["calculate_schedule", "predict_sunset_beauty"]


@trace()
async def send_locations_to_analysis_tasks(state: State):
  """Send the weather data from individual locations to the analyze_weather node."""
  return [
    Send(
      "analyze_weather",
      LocationWeatherState(
        day_start_ts=state.day_start_ts,
        weather_key=key,
        reports=reports,
      ),
    )
    for (key, reports) in state.regional_weather.reports_by_location.items()
  ]


@trace()
async def calculate_schedule(state: State):
  weather_report = state.regional_weather.reports_for_location(state.briefing_day_location)[0]
  output = await get_scheduler_agent().run(
    SchedulerInput(
      scheduling_date=state.day_start_ts,
      home_location=state.briefing_day_location,
      calendars=assert_not_none(state.calendars),
      hourly_weather_api_result=assert_not_none(weather_report.comfort_api_result),
    )
  )
  return {"schedule": output.schedule}


@trace()
async def analyze_weather(state: LocationWeatherState):
  analysis = await get_meteorologist_agent().run(
    MeteorologistInput(
      report_date=state.day_start_ts,
      weather_report=state.reports,
    )
  )
  return {
    "regional_weather": RegionalWeatherReports(
      analysis_by_location={state.weather_key: analysis},
    )
  }


@trace()
async def predict_sunset_beauty(state: State):
  weather_reports = state.regional_weather.reports_for_location(state.briefing_day_location)
  if not weather_reports:
    raise ValueError(
      f"No weather reports available for {state.briefing_day_location} on {state.day_start_ts}"
    )

  weather_report = weather_reports[0]
  sunset_prediction = await get_sunset_oracle_agent().run(
    SunsetOracleInput(
      prediction_date=state.day_start_ts,
      weather_report=weather_report.weather_report_api_result,
      air_quality_report=assert_not_none(weather_report.air_quality_api_result),
    )
  )
  return {"sunset_prediction": sunset_prediction}


@trace()
async def prioritize_events(state: State):
  prioritized_events = await get_event_prioritizer_agent().run(
    EventPrioritizerInput(
      schedule=assert_not_none(state.schedule),
      calendars_of_interest=assert_not_none(state.calendars),
      regional_weather_reports=assert_not_none(state.regional_weather),
      yesterdays_events=assert_not_none(state.yesterdays_events),
    )
  )
  return {"prioritized_events": prioritized_events}


@trace()
async def write_briefing_outline(state: State):
  sectioner = get_sectioner_agent()
  input = SectionerInput(
    schedule=assert_not_none(state.schedule),
    prioritized_events=assert_not_none(state.prioritized_events),
    regional_weather_reports=assert_not_none(state.regional_weather),
    sunset_predication=assert_not_none(state.sunset_prediction),
    yesterdays_events=assert_not_none(state.yesterdays_events),
  )
  out = await sectioner.run(input=input)
  return {"briefing_outline": out}


@trace()
async def write_briefing_script(state: State):
  weather_analysis = state.regional_weather.analysis_by_location
  out = await get_script_writer_agent().run(
    input=ScriptWriterInput(
      briefing_outline=assert_not_none(state.briefing_outline),
      prioritized_events=assert_not_none(state.prioritized_events),
      schedule=assert_not_none(state.schedule),
      weather_report=assert_not_none(
        weather_analysis[weather_key_for_location(state.briefing_day_location)]
      ),
      sunset_prediction=assert_not_none(state.sunset_prediction),
      character_pool=CHARACTER_POOL,
      previous_scripts=[],
    )
  )

  return {"briefing_script": out}


standard_retry = RetryPolicy(max_attempts=3)

location_graph_builder = StateGraph(LocationDataState)
location_graph_builder.add_node(resolve_location)
location_graph_builder.add_node(request_weather, retry=standard_retry)

location_graph_builder.set_entry_point("resolve_location")
location_graph_builder.add_edge("resolve_location", "request_weather")
location_graph_builder.set_finish_point("request_weather")

location_graph = location_graph_builder.compile()

builder = StateGraph(State)
builder.add_node(populate_raw_inputs, cache_policy=CachePolicy(ttl=120 * 60))
builder.add_node(process_location)
builder.add_node(fork_analysis, defer=True)
builder.add_node(calculate_schedule, retry=standard_retry)
builder.add_node(analyze_weather, retry=standard_retry)
builder.add_node(predict_sunset_beauty, retry=standard_retry)
builder.add_node(prioritize_events, defer=True)
builder.add_node(write_briefing_outline)
builder.add_node(write_briefing_script)

builder.set_entry_point("populate_raw_inputs")
builder.add_conditional_edges(
  "populate_raw_inputs", send_location_requests, then="process_location"
)
builder.add_edge("process_location", "fork_analysis")
builder.add_edge("populate_raw_inputs", "fork_analysis")
builder.add_conditional_edges(
  "fork_analysis",
  send_to_analysis_tasks,
  {
    "calculate_schedule": "calculate_schedule",
    "predict_sunset_beauty": "predict_sunset_beauty",
  },
)
builder.add_conditional_edges(
  "fork_analysis",
  send_locations_to_analysis_tasks,
  {"analyze_weather": "analyze_weather"},
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


@dataclass
class PrintMermaid:
  pass


type WorkflowCommand = Run | ListCheckpoints | PrintMermaid


def config_for_date(briefing_date: date) -> RunnableConfig:
  """Create a configuration for the workflow based on the briefing date."""

  return {
    "configurable": {
      "thread_id": briefing_date.isoformat() + f"+{random.randbytes(4).hex()}",
      # "checkpoint_id": "1f03c061-e828-6d6b-8009-f87baade1033",
    }
  }


async def run_workflow_command(cmd: WorkflowCommand) -> None:
  """Run the morning briefing workflow.

  Args:
      briefing_date: The date for which to run the briefing.
  """

  pg_connection_string = get_postgres_connection_string()
  async with (
    AsyncPostgresSaver.from_conn_string(
      pg_connection_string,
      serde=JsonPlusSerializer(pickle_fallback=True),
    ) as saver,
    AsyncPostgresStore.from_conn_string(pg_connection_string) as store,
  ):
    await asyncio.gather(store.setup(), saver.setup())

    graph = builder.compile(
      cache=SqliteCache(path=str(APP_DIRS.user_cache_path / "cache.db")),
      checkpointer=saver,
      store=store,
    )

    match cmd:
      case Run(briefing_date, location):
        config: RunnableConfig = config_for_date(briefing_date)
        config["callbacks"] = [CallbackHandler()]

        day_start_ts = start_of_local_day(briefing_date)
        # Run the workflow with a state update

        latest_state = await graph.aget_state(config)
        checkpoint_id = latest_state.config.get("configurable", {}).get("checkpoint_id", None)
        rich.print(f"Checkpoint ID: {checkpoint_id}")

        # if checkpoint_id:
        #   if "configurable" not in config:
        #     config["configurable"] = {}
        #   config["configurable"]["checkpoint_id"] = checkpoint_id

        with langfuse_span("graph"):
          state_dict = await graph.ainvoke(
            input=State(
              day_start_ts=day_start_ts,
              day_end_ts=end_of_local_day(day_start_ts),
              briefing_day_location=cast(ResolvedLocation, location),
            ),
            config=config,
            stream_mode="updates",
          )

          briefing = state_dict[-1]["write_briefing_script"]["briefing_script"]  # type: ignore
          rich.print(briefing)
          rich.print(BriefingScript.model_validate(briefing).model_dump_json(indent=2))  # type: ignore

      case ListCheckpoints(briefing_date):
        config = config_for_date(briefing_date)
        async for checkpoint in saver.alist(config=config):
          print(checkpoint.config)

      case PrintMermaid():
        rich.print(graph.get_graph().draw_mermaid())
