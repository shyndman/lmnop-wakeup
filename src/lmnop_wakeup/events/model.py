from collections.abc import Generator
from datetime import date
from typing import Any, NewType

from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from pydantic_extra_types.timezone_name import TimeZoneName

from lmnop_wakeup.core.date import TimeInfo, end_of_local_day, start_of_local_day

from ..location.model import AddressLocation, CoordinateLocation
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


class CalendarEvent(BaseModel):
  """Represents a single calendar event."""

  event_id: CalendarEventId
  """Uniquely identifies the event in its calendar"""
  summary: str
  """A brief summary or title of the event."""
  creator: CalendarEmailUser | None = None
  """The creator of the event."""
  attendees: list[CalendarUser] | None = None
  """A list of attendees for the event."""
  start_ts: TimeInfo = Field(alias="start")
  """The start time information of the event."""
  end_ts: TimeInfo | None = Field(None, alias="end")
  """The end time information of the event. None for all-day events."""
  description: str | None = None
  """A detailed description of the event."""
  location: str | None = None
  """The physical location of the event."""

  def is_all_day(self) -> bool:
    """Checks if the event is an all-day event."""
    return self.end_ts is None

  @property
  def start_datetime_aware(self) -> AwareDatetime:
    """
    Returns the timezone-aware start datetime of the event.
    For all-day events, this is the start of the day.
    """
    if self.is_all_day():
      return start_of_local_day(self.start_ts.to_aware_datetime())
    return self.start_ts.to_aware_datetime()

  @property
  def end_datetime_aware(self) -> AwareDatetime:
    """
    Returns the timezone-aware end datetime of the event.
    For all-day events, this is the end of the day.
    """
    if self.is_all_day():
      return end_of_local_day(self.start_ts.to_aware_datetime())
    if self.end_ts is None:
      raise ValueError("End time is not set for this event, and it is not an all-day event.")
    return self.end_ts.to_aware_datetime()

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
    have events in the given time range.

    Args:
      start_ts: The start of the time range to filter by.
      end_ts: The end of the time range to filter by.

    Returns:
      A list of CalendarEvent objects that overlap with the given time range.
    """
    return [event for event in self.events if event.overlaps_with_range(start_ts, end_ts)]


class CalendarsOfInterest(BaseModel):
  """Represents a collection of calendars."""

  calendars_by_id: dict[str, Calendar] = {}
  """A dictionary mapping calendar entity IDs to Calendar objects."""

  def __init__(self, *args, calendars: list[Calendar] | None = None, **kwargs):
    if "calendars_by_id" not in kwargs and calendars is not None:
      self.calendars_by_id = {calendar.entity_id: calendar for calendar in calendars}
    super().__init__(*args, **kwargs)

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

  origin: AddressLocation | CoordinateLocation
  """The starting location for the route."""

  destination: AddressLocation | CoordinateLocation
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
