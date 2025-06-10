import textwrap
from collections.abc import Generator
from datetime import date, datetime
from io import StringIO
from typing import Any, NewType, TypedDict

from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from pydantic_extra_types.timezone_name import TimeZoneName

from lmnop_wakeup.core.relative_dates import format_relative_date

from ..core.date import TimeInfo, end_of_local_day, format_time_info, start_of_local_day
from ..location.model import CoordinateLocation
from ..location.routes_api import CyclingRouteDetails, RouteDetails


class CalendarEmailUser(BaseModel):
  """Represents a user with an email address."""

  email: EmailStr
  """The email address of the user."""


class CalendarUser(CalendarEmailUser):
  """Represents a calendar user with a display name and email."""

  display_name: str = Field(alias="displayName")
  """The display name of the user."""
  email: EmailStr
  """The email address of the user."""


CalendarEventId = NewType("CalendarEventId", str)


class PrivateExtendedPropertiesDict(TypedDict, total=False):
  blogto_event: str
  intended_audience: str
  is_top_pick: str
  category: str
  state_hash: int


class ExtendedPropertiesDict(TypedDict, total=True):
  private: PrivateExtendedPropertiesDict | None


class CalendarEvent(BaseModel):
  """Represents a single calendar event."""

  id: str
  """Uniquely identifies the event in its calendar"""
  summary: str
  """A brief summary or title of the event."""

  description: str | None = None
  """A detailed description of the event."""

  creator: CalendarEmailUser | None = None
  """The creator of the event."""

  attendees: list[CalendarEmailUser] | None = None
  """A list of attendees for the event."""

  location: str | None = None
  """The physical location of the event."""

  source_url: str | None = Field(default=None, serialization_alias="source.url")
  """A URL related to the event, such as a meeting link or additional information."""

  start: TimeInfo
  """The start time information of the event."""

  end: TimeInfo | None = None
  """The end time information of the event. None for all-day events."""

  extended_properties: ExtendedPropertiesDict | None = None

  def is_all_day(self) -> bool:
    """Checks if the event is an all-day event."""
    return self.end is None

  @property
  def start_datetime_aware(self) -> AwareDatetime:
    """
    Returns the timezone-aware start datetime of the event.
    For all-day events, this is the start of the day.
    """
    if self.is_all_day():
      return start_of_local_day(self.start.to_aware_datetime())
    return self.start.to_aware_datetime()

  @property
  def end_datetime_aware(self) -> AwareDatetime:
    """
    Returns the timezone-aware end datetime of the event.
    For all-day events, this is the end of the day.
    """
    if self.is_all_day():
      return end_of_local_day(self.start.to_aware_datetime())
    if self.end is None:
      raise ValueError("End time is not set for this event, and it is not an all-day event.")
    return self.end.to_aware_datetime()

  def overlaps_with_range(self, range_start: AwareDatetime, range_end: AwareDatetime) -> bool:
    """
    Checks if the event's time range overlaps with a given range.

    Args:
      range_start: The start of the range to check against.
      range_end: The end of the range to check against.

    Returns:
      True if the event overlaps with the given range, False otherwise.
    """
    return self.start_datetime_aware < range_end and self.end_datetime_aware > range_start

  def model_dump_markdown(self, briefing_date: datetime) -> str:
    """
    Dumps the event details in a markdown format.

    Returns:
      A string containing the event details formatted in markdown.
    """
    sb = StringIO()
    event_time = format_time_info(self.start, "%Y-%m-%d", "%H:%M:%S")
    if self.end:
      event_time += " to "
      event_time += textwrap.dedent(format_time_info(self.end, "%Y-%m-%d", "%H:%M:%S"))

    relative_detes = "**Casual sounding ways to refer to the date:**\n" + "\n".join(
      f"        - {desc}"
      for desc in format_relative_date(
        briefing_date.date(), self.start.date or self.start.to_aware_datetime()
      )
    )
    # event_time += f"\nDays until event: {time_until.days}"

    sb.write(
      textwrap.dedent(f"""
      * ### {self.summary}
        id: {self.id}

        {event_time}
        {relative_detes}

      """).lstrip()
    )

    if self.description:
      sb.write("  **Description:**\n")
      sb.write(f"  {self.description}\n\n")

    if self.location:
      sb.write(f"  **Location:** {self.location}\n\n")

    creator = self.creator
    if creator:
      sb.write(f"\n**Created by:** {creator.email}\n")

    if self.attendees:
      attendees_list = ", ".join([f"{attendee.email}" for attendee in self.attendees])
      sb.write(f"**Attendees:** {attendees_list}\n")

    return sb.getvalue()


class Calendar(BaseModel):
  """Represents a single calendar."""

  entity_id: str
  """The unique identifier for the calendar."""
  name: str
  """The name of the calendar."""
  events: list[CalendarEvent] = []
  """A list of events associated with this calendar."""
  time_zone: TimeZoneName | None = None
  """The time zone of the calendar."""
  notes_for_processing: str | None = None
  """Any notes relevant for processing this calendar."""

  def filter_events_by_range(
    self, start_ts: AwareDatetime, end_ts: AwareDatetime
  ) -> list[CalendarEvent]:
    """
    Filters the events within this calendar to only include those that
    have events in the given time range, and returns them in a new list.

    Args:
      start_ts: The start of the time range to filter by.
      end_ts: The end of the time range to filter by.

    Returns:
      A list of CalendarEvent objects that overlap with the given time range.
    """
    return [event for event in self.events if event.overlaps_with_range(start_ts, end_ts)]

  def model_dump_markdown(self, briefing_date: datetime) -> str:
    sb = StringIO()
    sb.write(
      textwrap.dedent(f"""
      --------------------------------

      ## {self.name}

      > {self.notes_for_processing}


      """).lstrip()
    )

    for event in self.events:
      sb.write(event.model_dump_markdown(briefing_date))
      sb.write("\n\n")

    return sb.getvalue()


class CalendarsOfInterest(BaseModel):
  """Represents a collection of calendars."""

  calendars_by_id: dict[str, Calendar] = {}
  """A dictionary mapping calendar entity IDs to Calendar objects."""

  def all_events_with_location(self) -> Generator[CalendarEvent, Any, None]:
    for cal in self.calendars_by_id.values():
      for event in cal.events:
        if event.location:
          yield event

  def filter(
    self,
    start_ts: AwareDatetime,
    end_ts: AwareDatetime,
    name_inclusion_list: set[str] | None = None,
  ) -> "CalendarsOfInterest":
    """
    Filters the calendars in this set to only include those that have events
    in the given time range and optionally match a name inclusion list.

    Args:
      start_ts: The start of the time range to filter by.
      end_ts: The end of the time range to filter by.
      name_inclusion_list: An optional set of calendar names to include.
                           If None, all calendars are considered.

    Returns:
      A new CalendarSet containing only the filtered calendars and their events.
    """
    filtered_calendars = {}
    for entity_id, calendar in self.calendars_by_id.items():
      if name_inclusion_list is not None and calendar.name not in name_inclusion_list:
        continue

      filtered_events = calendar.filter_events_by_range(start_ts, end_ts)

      if filtered_events:
        filtered_calendar = calendar.model_copy(deep=True)
        filtered_calendar.events = filtered_events
        filtered_calendars[entity_id] = filtered_calendar

    return CalendarsOfInterest(calendars_by_id=filtered_calendars)

  def model_dump_markdown(self, briefing_date: datetime) -> str:
    sb = StringIO()
    for cal in self.calendars_by_id.values():
      if not cal.events:
        continue

      sb.write(cal.model_dump_markdown(briefing_date))

    return sb.getvalue()


class ModeRejectionResult(BaseModel):
  """A data structure representing an LLM's rationale for rejecting a particular transportation
  mode.

  Attributes:
    rejection_rationale (str): A human-readable explanation for why a specific
      transportation mode was deemed unsuitable by the LLM.
  """

  rejection_rationale: str
  """Two sentences max, specifically describing the broken rule that lead to the rejection"""


class EventRouteOptions(BaseModel):
  """Represents the available route options and details for travel between two locations.

  This structure is used by the Timekeeper LLM to understand the possible ways to travel
  for a scheduled event, including details for different transportation modes and
  reasons why a mode might be unsuitable.
  """

  origin: CoordinateLocation
  """The starting location for the route."""

  destination: CoordinateLocation
  """The ending location for the route."""

  related_event_id: list[str] = Field(min_length=1, max_length=2)
  """The identifier(s) of the calendar event(s) the user is travelling to or from, or both"""

  bike: CyclingRouteDetails | ModeRejectionResult
  """Route details for cycling, or a rejection result if cycling is not a viable option."""

  drive: RouteDetails
  """Route details for driving. A driving route is always expected to be available."""

  transit: RouteDetails | ModeRejectionResult
  """Route details for public transit, or a rejection result if transit is not a viable option."""

  walk: RouteDetails | ModeRejectionResult
  """Route details for walking, or a rejection result if walking is not a viable option."""


class Schedule(BaseModel):
  date: date
  """The day described by this schedule."""

  wakeup_time: AwareDatetime
  """The calculated time the user should wake up."""

  triggering_event_details: CalendarEvent | None
  """The calendar event that was used to determine the wakeup_time. This will be `null` if the
  wake-up time was based on the latest possible time rather than a specific event."""

  event_travel_routes: list[EventRouteOptions]
  """Details about the computed routes for travel related to the scheduled event(s)."""
