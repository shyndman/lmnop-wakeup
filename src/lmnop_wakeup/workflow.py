import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Literal, cast

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
from pydantic_extra_types.coordinate import Coordinate
from rich.prompt import Prompt

from . import APP_DIRS
from .audio.workflow import TTSWorkflowState, tts_graph
from .brief.actors import CHARACTER_POOL
from .brief.content_optimizer import (
  ContentOptimizerInput,
  get_content_optimizer,
)
from .brief.model import BriefingScript, ConsolidatedBriefingScript
from .brief.script_writer_agent import (
  ScriptWriterInput,
  get_script_writer_agent,
)
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
from .events.model import CalendarEvent, CalendarsOfInterest
from .events.prioritizer_agent import (
  EventPrioritizerInput,
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
from .paths import BriefingDirectory, BriefingDirectoryCollection
from .state import LocationDataState, LocationWeatherState, State
from .weather.meteorologist_agent import (
  MeteorologistInput,
  get_meteorologist_agent,
)
from .weather.model import weather_key_for_location
from .weather.sunset_oracle_agent import (
  SunsetOracleInput,
  get_sunset_oracle_agent,
)
from .weather.sunset_scoring import (
  SunsetAirQualityAPIResponse,
  SunsetWeatherAPIResponse,
  analyze_sunset_conditions,
)
from .weather.weather_api import get_weather_report

type RouteKey = tuple[str, Coordinate]
logger = structlog.get_logger()

FUTURE_EVENTS_TIMEDELTA = timedelta(days=12)
FUTURE_WEATHER_TIMEDELTA = timedelta(days=3)
PREVIOUS_SCRIPTS_COUNT = 1


class WorkflowAbortedByUser(Exception):
  """Exception raised when user aborts workflow during interactive review."""

  def __init__(self, message: str = "Workflow aborted by user"):
    self.message = message
    super().__init__(self.message)


def get_user_decision(prompt_text: str) -> Literal["continue", "abort", "rerun"]:
  """Get user decision for workflow continuation."""
  rich.print(f"\n[bold blue]{prompt_text}[/bold blue]")

  while True:
    choice = Prompt.ask(
      "Choose action [(c)ontinue/(a)bort/(r)erun]",
      choices=["continue", "c", "abort", "a", "rerun", "r"],
      show_choices=False,
      default="continue",
    )
    # Normalize single letter choices
    if choice == "c":
      return "continue"
    elif choice == "a":
      return "abort"
    elif choice == "r":
      return "rerun"
    elif choice in ["continue", "abort", "rerun"]:
      return choice  # type: ignore
    rich.print("[red]Invalid choice. Please select continue/c, abort/a, or rerun/r.[/red]")


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
      reports_by_location={weather_key_for_location(loc): [weather]}  # type: ignore
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

  if result.special_location_id is not None:
    if result.special_location_id not in LocationName:
      raise ValueError(f"Special location {result.special_location_id} is not a valid LocationName")
    return {
      "resolved_location": location_named(LocationName(result.special_location_id)),
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
async def review_prioritized_events(state: State):
  """Interrupt point after event prioritization for user review."""
  if state.prioritized_events is None:
    return {}

  rich.print("\n[bold green]📅 Prioritized Events Review[/bold green]")
  rich.print(state.prioritized_events.model_dump_json(indent=2))

  decision = get_user_decision("Review the prioritized events above.")

  if decision == "abort":
    rich.print("[yellow]Workflow aborted by user.[/yellow]")
    raise WorkflowAbortedByUser("User aborted workflow after reviewing prioritized events")
  elif decision == "rerun":
    rich.print("[yellow]Regenerating event prioritization...[/yellow]")
    return {"prioritized_events": None}

  # Continue - no changes needed
  return {}


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
async def review_content_optimization(state: State):
  """Interrupt point after content optimization for user review."""
  if state.content_optimization_report is None:
    return {}

  rich.print("\n[bold green]📊 Content Optimization Review[/bold green]")
  rich.print(state.content_optimization_report.model_dump_json(indent=2))

  decision = get_user_decision("Review the content optimization suggestions above.")

  if decision == "abort":
    rich.print("[yellow]Workflow aborted by user.[/yellow]")
    raise WorkflowAbortedByUser("User aborted workflow after reviewing content optimization")
  elif decision == "rerun":
    rich.print("[yellow]Regenerating content optimization...[/yellow]")
    return {"content_optimization_report": None}

  return {}


def _load_previous_scripts(briefing_date: date, count: int) -> list[BriefingScript]:
  """Load previous N consecutive days' scripts from disk, skipping missing ones."""

  previous_scripts = []
  collection = BriefingDirectoryCollection()

  for days_back in range(1, count + 1):
    previous_date = briefing_date - timedelta(days=days_back)
    briefing_dir = collection.get_existing_for_date(previous_date)

    if briefing_dir and briefing_dir.has_brief_json():
      try:
        script = briefing_dir.load_script()
        previous_scripts.append(script)
        logger.debug("Loaded previous script", date=previous_date.isoformat())
      except Exception as e:
        logger.warning(
          "Failed to load previous script", date=previous_date.isoformat(), error=str(e)
        )
    else:
      logger.debug("No script found for previous date", date=previous_date.isoformat())

  return previous_scripts


@trace()
async def write_briefing_script(state: State, config: RunnableConfig):
  weather_analysis = state.regional_weather.analysis_by_location

  # Load previous scripts from consecutive days
  briefing_date = state.day_start_ts.date()
  previous_scripts = _load_previous_scripts(briefing_date, PREVIOUS_SCRIPTS_COUNT)

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
      previous_scripts=previous_scripts,
      calendars_of_interest=assert_not_none(state.calendars),
    )
  )
  return {"briefing_script": script}


@trace()
async def review_briefing_script(state: State):
  """Interrupt point after script generation for user review."""
  if state.briefing_script is None:
    return {}

  rich.print("\n[bold green]📝 Briefing Script Review[/bold green]")
  rich.print(state.briefing_script.build_display_text())

  decision = get_user_decision("Review the generated briefing script above.")

  if decision == "abort":
    rich.print("[yellow]Workflow aborted by user.[/yellow]")
    raise WorkflowAbortedByUser("User aborted workflow after reviewing briefing script")
  elif decision == "rerun":
    rich.print("[yellow]Regenerating briefing script...[/yellow]")
    return {"briefing_script": None}

  return {}


@trace()
async def consolidate_dialogue(state: State, config: RunnableConfig):
  if state.briefing_script is not None:
    return {"consolidated_briefing_script": state.briefing_script.consolidate_dialogue()}
  return None


@trace()
async def review_final_script(state: State):
  """Interrupt point after script consolidation for final review."""
  if state.consolidated_briefing_script is None:
    return {}

  rich.print("\n[bold green]🎬 Final Script Review[/bold green]")
  rich.print(state.consolidated_briefing_script.build_display_text())

  decision = get_user_decision("Review the final consolidated script above before TTS generation.")

  if decision == "abort":
    rich.print("[yellow]Workflow aborted by user.[/yellow]")
    raise WorkflowAbortedByUser("User aborted workflow after reviewing final script")
  elif decision == "rerun":
    rich.print("[yellow]Regenerating script consolidation...[/yellow]")
    return {"consolidated_briefing_script": None}

  return {}


@trace()
async def generate_tts(state: State):
  """Generate TTS audio by invoking the TTS subgraph."""
  logger.info("Invoking TTS subgraph")

  if state.consolidated_briefing_script is None:
    raise ValueError("No consolidated briefing script available for TTS generation")

  # Create minimal TTS state
  tts_state = TTSWorkflowState(
    consolidated_briefing_script=state.consolidated_briefing_script,
    day_start_ts=state.day_start_ts,
  )

  # Invoke TTS subgraph
  result = TTSWorkflowState.model_validate(await tts_graph.ainvoke(tts_state))

  # Return partial update for the main state
  return {"tts": result.tts}


@trace()
async def schedule_automation_calendar_events(state: State, config: RunnableConfig):
  schedule = state.schedule
  if schedule is None:
    raise ValueError("No schedule available to write calendar events")

  wakeup_event = CalendarEvent(
    id=f"up{schedule.date.isoformat().replace('-', '')}",
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


# Routing functions for conditional edges in interactive mode


def route_after_prioritized_events_review(state: State) -> str:
  """Route after prioritized events review."""
  return "prioritize_events" if state.prioritized_events is None else "write_content_optimization"


def route_after_content_optimization_review(state: State) -> str:
  """Route after content optimization review."""
  return (
    "write_content_optimization"
    if state.content_optimization_report is None
    else "write_briefing_script"
  )


def route_after_briefing_script_review(state: State) -> str:
  """Route after briefing script review."""
  return "write_briefing_script" if state.briefing_script is None else "consolidate_dialogue"


def route_after_final_script_review(state: State) -> str:
  """Route after final script review."""
  return "consolidate_dialogue" if state.consolidated_briefing_script is None else "generate_tts"


async def find_incomplete_thread_for_date(saver, briefing_date: date) -> str | None:
  """Find the most recent incomplete thread for a given date."""
  try:
    # Get all threads that start with the briefing date
    date_prefix = briefing_date.isoformat()

    # List all checkpoints and find threads for this date
    checkpoints = []
    all_thread_ids = []
    async for checkpoint in saver.alist({}):
      thread_id = checkpoint.config.get("configurable", {}).get("thread_id", "")
      all_thread_ids.append(thread_id)
      if thread_id.startswith(date_prefix):
        checkpoints.append(checkpoint)

    logger.debug(
      f"Looking for threads with prefix '{date_prefix}'. Found thread IDs: {all_thread_ids[:10]}"
    )  # Show first 10

    if not checkpoints:
      return None

    # Sort by timestamp (most recent first) and check if any are incomplete
    checkpoints.sort(key=lambda c: c.checkpoint["ts"], reverse=True)

    for checkpoint in checkpoints:
      # Check if this checkpoint represents an incomplete workflow
      # A complete workflow should have reached the finish point
      thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
      logger.debug(f"=== Checkpoint dump for thread {thread_id} ===")
      logger.debug(f"Checkpoint: {checkpoint.checkpoint}")
      logger.debug(f"Config: {checkpoint.config}")
      if hasattr(checkpoint, "metadata"):
        logger.debug(f"Metadata: {checkpoint.metadata}")
      logger.debug("=== End checkpoint dump ===")

      # For now, let's just return the first one to see what a checkpoint looks like
      logger.info(f"Found thread for {briefing_date}: {thread_id}")
      return thread_id

    return None
  except Exception as e:
    logger.warning(f"Error finding incomplete threads for {briefing_date}: {e}")
    return None


async def is_thread_complete(graph, thread_id: str) -> bool:
  """Check if a thread is complete by examining its state snapshot."""
  try:
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = await graph.aget_state(config)

    # A complete workflow has no next nodes to execute
    is_complete = not state_snapshot.next
    logger.debug(f"Thread {thread_id} complete: {is_complete}, next: {state_snapshot.next}")
    return is_complete

  except Exception as e:
    logger.warning(f"Error checking if thread {thread_id} is complete: {e}")
    return False


def config_for_date(briefing_date: date, thread_id: str | None = None) -> RunnableConfig:
  """Create a configuration for the workflow based on the briefing date."""

  if thread_id is None:
    thread_id = f"{briefing_date.isoformat()}"

  return {
    "configurable": {
      "thread_id": thread_id,
    }
  }


def build_graph(interactive: bool = False):
  """Build the workflow graph with optional human-in-the-loop review steps."""
  two_hour_cache = CachePolicy(ttl=120 * 60)

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
  graph_builder.add_node(generate_tts)
  graph_builder.add_node(schedule_automation_calendar_events, retry=standard_retry)

  # Add review nodes if in interactive mode
  if interactive:
    graph_builder.add_node(review_prioritized_events)
    graph_builder.add_node(review_content_optimization)
    graph_builder.add_node(review_briefing_script)
    graph_builder.add_node(review_final_script)

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

  # Wire up the content generation flow based on interactive mode
  if interactive:
    # Interactive mode: generation → review → conditional routing
    graph_builder.add_edge("prioritize_events", "review_prioritized_events")
    graph_builder.add_conditional_edges(
      "review_prioritized_events",
      route_after_prioritized_events_review,
      {
        "prioritize_events": "prioritize_events",
        "write_content_optimization": "write_content_optimization",
      },
    )

    graph_builder.add_edge("write_content_optimization", "review_content_optimization")
    graph_builder.add_conditional_edges(
      "review_content_optimization",
      route_after_content_optimization_review,
      {
        "write_content_optimization": "write_content_optimization",
        "write_briefing_script": "write_briefing_script",
      },
    )

    graph_builder.add_edge("write_briefing_script", "review_briefing_script")
    graph_builder.add_conditional_edges(
      "review_briefing_script",
      route_after_briefing_script_review,
      {
        "write_briefing_script": "write_briefing_script",
        "consolidate_dialogue": "consolidate_dialogue",
      },
    )

    graph_builder.add_edge("consolidate_dialogue", "review_final_script")
    graph_builder.add_conditional_edges(
      "review_final_script",
      route_after_final_script_review,
      {"consolidate_dialogue": "consolidate_dialogue", "generate_tts": "generate_tts"},
    )
  else:
    # Non-interactive mode: direct linear flow
    graph_builder.add_edge("prioritize_events", "write_content_optimization")
    graph_builder.add_edge("write_content_optimization", "write_briefing_script")
    graph_builder.add_edge("write_briefing_script", "consolidate_dialogue")
    graph_builder.add_edge("consolidate_dialogue", "generate_tts")

  graph_builder.add_edge("generate_tts", "schedule_automation_calendar_events")
  graph_builder.set_finish_point("schedule_automation_calendar_events")

  return graph_builder


async def run_workflow(
  briefing_date: date,
  briefing_location: CoordinateLocation,
  thread_id: str | None = None,
  interactive: bool = False,
  force_new_thread_id: bool = False,
) -> tuple[ConsolidatedBriefingScript | None, State]:
  """Run the morning briefing workflow.

  Args:
      briefing_date: The date for which to run the briefing.
      briefing_location: The location for the briefing.
      thread_id: Optional thread ID to continue existing workflow.
      interactive: Whether to enable human-in-the-loop interactions.
      force_new_thread_id: If True, always create a new thread ID instead of
        auto-discovering incomplete threads.
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
    graph_builder = build_graph(interactive=interactive)
    graph = graph_builder.compile(
      cache=SqliteCache(path=str(APP_DIRS.user_cache_path / "cache.db")),
      checkpointer=saver,
      store=store,
    )

    # Handle thread_id logic: use provided thread_id, or find incomplete thread, or create new
    if thread_id is None:
      if force_new_thread_id:
        logger.info(f"Forcing new thread creation for {briefing_date}")
      else:
        found_thread_id = await find_incomplete_thread_for_date(saver, briefing_date)
        if found_thread_id:
          logger.info(f"Continuing incomplete thread: {found_thread_id}")
          thread_id = found_thread_id
        else:
          logger.info(
            f"No incomplete threads found for {briefing_date}, checking for complete threads"
          )
          # Check if the default thread ID would be complete
          thread_id = f"{briefing_date.isoformat()}"
    else:
      logger.info(f"Using provided thread_id: {thread_id}")

    # Check if the thread is already complete and create a new one if needed
    if thread_id and await is_thread_complete(graph, thread_id):
      logger.info(f"Thread {thread_id} is already complete, creating new thread")
      # Generate a new unique thread ID by appending a timestamp
      from datetime import datetime

      timestamp = datetime.now().strftime("%H%M%S")
      thread_id = f"{briefing_date.isoformat()}-{timestamp}"
      logger.info(f"Starting new thread: {thread_id}")

    config: RunnableConfig = config_for_date(briefing_date, thread_id)
    config["callbacks"] = [CallbackHandler(), PydanticAiCallback()]

    day_start_ts = start_of_local_day(briefing_date)

    # Check if we have an existing checkpoint state
    latest_state = await graph.aget_state(config)
    checkpoint_id = latest_state.config.get("configurable", {}).get("checkpoint_id", None)
    has_existing_state = latest_state.values is not None and len(latest_state.values) > 0

    rich.print(f"Checkpoint ID: {checkpoint_id}")
    rich.print(f"Has existing state: {has_existing_state}")

    with langfuse_span("graph"):
      if has_existing_state:
        logger.info(f"Continuing from existing checkpoint: {checkpoint_id}")
        # Don't provide state - let it resume from checkpoint
        result = await graph.ainvoke(
          None,  # No initial state - continue from checkpoint
          config=config,
          checkpoint_during=True,
          debug=True,
        )
      else:
        logger.info("Starting new workflow with initial state")
        # Provide initial state for new workflow
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
