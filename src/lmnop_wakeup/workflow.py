import asyncio
import itertools
import operator
import random
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal, cast

import rich
import structlog
from langchain_core.runnables import RunnableConfig
from langfuse.langchain import CallbackHandler
from langgraph.cache.sqlite import SqliteCache
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import StateGraph
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.types import CachePolicy, RetryPolicy, Send
from pydantic import AwareDatetime, BaseModel, computed_field
from pydantic_extra_types.coordinate import Coordinate

from . import APP_DIRS
from .brief.actors import CHARACTER_POOL
from .brief.content_optimizer import (
  ContentOptimizationReport,
  ContentOptimizerInput,
  get_content_optimizer,
)
from .brief.script_writer_agent import BriefingScript, ScriptWriterInput, get_script_writer_agent
from .core.date import TimeInfo, end_of_local_day, start_of_local_day
from .core.tracing import langfuse_span, trace
from .core.typing import assert_not_none, ensure
from .env import get_postgres_connection_string
from .events.calendar.gcalendar_api import (
  AUTOMATION_SCHEDULER_CALENDAR_ID,
  get_calendar_event,
  insert_calendar_event,
  update_calendar_event,
)
from .events.events_api import get_filtered_calendars_with_notes
from .events.model import CalendarEvent, CalendarsOfInterest, Schedule
from .events.prioritizer_agent import (
  EventPrioritizerInput,
  PrioritizedEvents,
  RegionalWeatherReports,
  get_event_prioritizer_agent,
)
from .events.scheduler_agent import SchedulerInput, get_scheduler_agent
from .llm import PydanticAiCallback
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
from .paths import BriefingDirectory
from .weather.meteorologist_agent import (
  MeteorologistInput,
  get_meteorologist_agent,
)
from .weather.model import WeatherKey, weather_key_for_location
from .weather.sunset_oracle_agent import (
  SunsetOracleInput,
  SunsetPrediction,
  get_sunset_oracle_agent,
)
from .weather.sunset_scoring import (
  SunsetAirQualityAPIResponse,
  SunsetAnalysisResult,
  SunsetWeatherAPIResponse,
  analyze_sunset_conditions,
)
from .weather.weather_api import WeatherReport, get_weather_report

type RouteKey = tuple[str, Coordinate]
logger = structlog.get_logger()


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

  consolidated_briefing_script: BriefingScript | None = None
  """The final script for the briefing, with its dialog consolidated."""

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
FUTURE_WEATHER_TIMEDELTA = timedelta(days=3)


@trace()
async def populate_raw_inputs(state: State):
  span_end = state.day_end_ts + FUTURE_EVENTS_TIMEDELTA
  weather_span_end = state.day_end_ts + FUTURE_WEATHER_TIMEDELTA

  local_weather = await get_weather_report(
    location=state.briefing_day_location,
    report_start_ts=state.day_start_ts,
    report_end_ts=weather_span_end,
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
  logger.info(f"Processing {new_state.address}")

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
async def resolve_location(state: LocationDataState, config: RunnableConfig):
  location_resolver = get_location_resolver_agent(config)
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
async def calculate_schedule(state: State, config: RunnableConfig):
  weather_report = state.regional_weather.reports_for_location(state.briefing_day_location)[0]
  output = await get_scheduler_agent(config).run(
    SchedulerInput(
      scheduling_date=state.day_start_ts,
      home_location=state.briefing_day_location,
      calendars=assert_not_none(state.calendars),
      hourly_weather_api_result=assert_not_none(weather_report.comfort_api_result),
    )
  )
  return {"schedule": output.schedule}


@trace()
async def analyze_weather(state: LocationWeatherState, config: RunnableConfig):
  analysis = await get_meteorologist_agent(config).run(
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
async def predict_sunset_beauty(state: State, config: RunnableConfig):
  weather_reports = state.regional_weather.reports_for_location(state.briefing_day_location)
  if not weather_reports:
    raise ValueError(
      f"No weather reports available for {state.briefing_day_location} on {state.day_start_ts}"
    )

  weather_report = weather_reports[0]
  if weather_report.air_quality_api_result is None:
    raise ValueError(
      f"No air quality report available for {state.briefing_day_location} on {state.day_start_ts}"
    )
  weather_report.weather_report_api_result = weather_report.weather_report_api_result
  sunset_analysis = analyze_sunset_conditions(
    state.day_start_ts.date(),
    SunsetWeatherAPIResponse.model_validate_json(weather_report.weather_report_api_result),
    SunsetAirQualityAPIResponse.model_validate_json(weather_report.air_quality_api_result),
  )

  sunset_prediction = await get_sunset_oracle_agent(config).run(
    SunsetOracleInput(prediction_date=state.day_start_ts, sunset_analysis=sunset_analysis)
  )
  return {"sunset_analysis": sunset_analysis, "sunset_prediction": sunset_prediction}


@trace()
async def prioritize_events(state: State, config: RunnableConfig):
  prioritized_events = await get_event_prioritizer_agent(config).run(
    EventPrioritizerInput(
      schedule=assert_not_none(state.schedule),
      calendars_of_interest=assert_not_none(state.calendars),
      regional_weather_reports=assert_not_none(state.regional_weather),
      yesterdays_events=assert_not_none(state.yesterdays_events),
    )
  )
  return {"prioritized_events": prioritized_events}


@trace()
async def write_content_optimization(state: State, config: RunnableConfig):
  sectioner = get_content_optimizer(config)
  input = ContentOptimizerInput(
    schedule=assert_not_none(state.schedule),
    prioritized_events=assert_not_none(state.prioritized_events),
    regional_weather_reports=assert_not_none(state.regional_weather),
    sunset_predication=assert_not_none(state.sunset_prediction),
  )
  logger.warning(input.model_dump_json(indent=2))
  out = await sectioner.run(input=input)
  return {"content_optimization_report": out}


@trace()
async def write_briefing_script(state: State, config: RunnableConfig):
  weather_analysis = state.regional_weather.analysis_by_location
  script = await get_script_writer_agent(config).run(
    input=ScriptWriterInput(
      content_optimizer_report=assert_not_none(state.content_optimization_report),
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
  return {"briefing_script": script}


@trace()
async def consolidate_dialogue(state: State, config: RunnableConfig):
  if state.briefing_script is not None:
    return {"consolidated_briefing_script": state.briefing_script.consolidate_dialogue()}
  return None


@trace()
async def schedule_automation_calendar_events(state: State, config: RunnableConfig):
  schedule = state.schedule
  if schedule is None:
    raise ValueError("No schedule available to write calendar events")

  wakeup_event = CalendarEvent(
    id=f"lmnop_up_{schedule.date.isoformat()}",
    summary=f"lmnop:wakeup({schedule.date.isoformat()})",
    start=TimeInfo(dateTime=schedule.wakeup_time),
    end=TimeInfo(dateTime=schedule.wakeup_time + timedelta(minutes=5)),
  )
  maybe_event = get_calendar_event(AUTOMATION_SCHEDULER_CALENDAR_ID, wakeup_event.id)
  if maybe_event:
    rich.print(f"Event {wakeup_event.id} already exists in calendar, updating.")
    update_calendar_event(calendar_id=AUTOMATION_SCHEDULER_CALENDAR_ID, event=wakeup_event)
  else:
    rich.print(f"Event {wakeup_event.id} is new, inserting.")
    insert_calendar_event(calendar_id=AUTOMATION_SCHEDULER_CALENDAR_ID, event=wakeup_event)


standard_retry = RetryPolicy(max_attempts=3)

location_graph_builder = StateGraph(LocationDataState)
location_graph_builder.add_node(resolve_location)
location_graph_builder.add_node(request_weather, retry=standard_retry)

location_graph_builder.set_entry_point("resolve_location")
location_graph_builder.add_edge("resolve_location", "request_weather")
location_graph_builder.set_finish_point("request_weather")

location_graph = location_graph_builder.compile()


def config_for_date(briefing_date: date) -> RunnableConfig:
  """Create a configuration for the workflow based on the briefing date."""

  return {
    "configurable": {
      "thread_id": f"{briefing_date.isoformat()}+{random.randbytes(4).hex()}",
    }
  }


def build_graph():
  two_hour_cache = CachePolicy(ttl=120 * 60)

  """Build the workflow graph with optional review step."""
  graph_builder = StateGraph(State)
  graph_builder.add_node(
    populate_raw_inputs, cache_policy=two_hour_cache, destinations=("process_location",)
  )
  graph_builder.add_node(process_location)
  graph_builder.add_node(fork_analysis, defer=True)
  graph_builder.add_node(calculate_schedule, retry=standard_retry)
  graph_builder.add_node(analyze_weather, retry=standard_retry, cache_policy=two_hour_cache)
  graph_builder.add_node(predict_sunset_beauty, retry=standard_retry, cache_policy=two_hour_cache)
  graph_builder.add_node(prioritize_events, defer=True)
  graph_builder.add_node(write_content_optimization, retry=standard_retry)
  graph_builder.add_node(write_briefing_script, retry=standard_retry)
  graph_builder.add_node(consolidate_dialogue)
  graph_builder.add_node(schedule_automation_calendar_events, retry=standard_retry)

  graph_builder.set_entry_point("populate_raw_inputs")
  graph_builder.add_conditional_edges(
    "populate_raw_inputs", send_location_requests, then="process_location"
  )
  graph_builder.add_edge("process_location", "fork_analysis")
  graph_builder.add_edge("populate_raw_inputs", "fork_analysis")
  graph_builder.add_conditional_edges(
    "fork_analysis",
    send_to_analysis_tasks,
    {
      "calculate_schedule": "calculate_schedule",
      "predict_sunset_beauty": "predict_sunset_beauty",
    },
  )
  graph_builder.add_conditional_edges(
    "fork_analysis",
    send_locations_to_analysis_tasks,
    {"analyze_weather": "analyze_weather"},
  )
  graph_builder.add_edge("calculate_schedule", "prioritize_events")
  graph_builder.add_edge("analyze_weather", "prioritize_events")
  graph_builder.add_edge("predict_sunset_beauty", "prioritize_events")
  graph_builder.add_edge("prioritize_events", "write_content_optimization")
  graph_builder.add_edge("write_content_optimization", "write_briefing_script")
  graph_builder.add_edge("write_briefing_script", "consolidate_dialogue")
  graph_builder.add_edge("consolidate_dialogue", "schedule_automation_calendar_events")
  graph_builder.set_finish_point("schedule_automation_calendar_events")

  return graph_builder


async def run_workflow(
  briefing_date: date,
  briefing_location: CoordinateLocation,
) -> tuple[BriefingScript | None, State]:
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

    # Build graph with conditional review step
    graph_builder = build_graph()
    graph = graph_builder.compile(
      cache=SqliteCache(path=str(APP_DIRS.user_cache_path / "cache.db")),
      checkpointer=saver,
      store=store,
    )

    config: RunnableConfig = config_for_date(briefing_date)
    config["callbacks"] = [CallbackHandler(), PydanticAiCallback()]

    day_start_ts = start_of_local_day(briefing_date)
    # Run the workflow with a state update

    latest_state = await graph.aget_state(config)
    checkpoint_id = latest_state.config.get("configurable", {}).get("checkpoint_id", None)
    rich.print(f"Checkpoint ID: {checkpoint_id}")

    with langfuse_span("graph"):
      result = await graph.ainvoke(
        State(
          day_start_ts=day_start_ts,
          day_end_ts=end_of_local_day(day_start_ts),
          briefing_day_location=cast(ResolvedLocation, briefing_location),
        ),
        config=config,
        checkpoint_during=True,
        debug=True,
      )
      final_state = State.model_validate(result)
      rich.print(final_state.model_dump())

      # Use BriefingDirectory for type-safe file operations
      briefing_dir = BriefingDirectory.for_date(briefing_date)
      briefing_dir.ensure_exists()

      logger.info(f"Saving state to {briefing_dir.workflow_state_path}")
      with open(briefing_dir.workflow_state_path, "w") as f:
        f.write(final_state.model_dump_json())
      logger.info(f"Saving brief to {briefing_dir.brief_json_path}")
      with open(briefing_dir.brief_json_path, "w") as f:
        f.write(final_state.briefing_script.model_dump_json())  # type: ignore
      logger.info(f"Saving consolidated brief to {briefing_dir.consolidated_brief_json_path}")
      with open(briefing_dir.consolidated_brief_json_path, "w") as f:
        f.write(final_state.consolidated_briefing_script.model_dump_json())  # type: ignore

      return final_state.consolidated_briefing_script, final_state
