from collections.abc import Sequence
from datetime import datetime, timedelta
from types import CoroutineType
from typing import Any

from google.auth.api_key import Credentials
from google.maps import routing_v2
from google.maps.routing import (
  ComputeRoutesRequest,
  ComputeRoutesResponse,
  RoutesAsyncClient,
  RouteTravelMode,
  RoutingPreference,
)
from google.protobuf.timestamp_pb2 import Timestamp
from pydantic import BaseModel, computed_field

from ..asyncio import gather_map
from ..locations import Location
from .calendars import ApiKey


class RouteDetails(BaseModel):
  departure_time: datetime
  arrival_time: datetime
  distance_meters: int

  @computed_field
  @property
  def duration(self) -> timedelta:
    return self.arrival_time - self.departure_time


CALORIES_CONSUMED_PER_KM = 23


class CyclingRouteDetails(RouteDetails):
  @property
  def calories_consumed(self):
    """Get the projected calorie consumption for the bike ride."""
    return CALORIES_CONSUMED_PER_KM * self.distance_meters / 1000


class DrivingRouteDetails(RouteDetails):
  pass


class RouteDetailsByMode(BaseModel):
  origin: Location
  destination: Location

  bike: CyclingRouteDetails | None
  drive: RouteDetails
  """We will always have a driving route, and if we don't, the tool will fail"""
  transit: RouteDetails | None
  walk: RouteDetails | None


type TimeConstraint = ArriveByConstraint | DepartAtConstraint


class ArriveByConstraint(BaseModel):
  time: datetime

  def estimated_departure_time(self) -> datetime:
    return self.time - timedelta(minutes=40)

  def resolve(self, trip_duration: timedelta) -> tuple[datetime, datetime]:
    arrival_time = self.time.replace()
    departure_time = arrival_time - trip_duration
    return (departure_time, arrival_time)


class DepartAtConstraint(BaseModel):
  time: datetime

  def estimated_departure_time(self) -> datetime:
    return self.time

  def resolve(self, trip_duration: timedelta) -> tuple[datetime, datetime]:
    departure_time = self.time.replace()
    arrival_time = departure_time + trip_duration
    return (departure_time, arrival_time)


async def compute_route_durations(
  google_routes_api_key: ApiKey,
  origin: Location,
  destination: Location,
  time_constraint: TimeConstraint,
  include_cycling: bool,
  include_transit: bool,
  include_walking: bool,
) -> RouteDetailsByMode:
  # Create a client
  client = routing_v2.RoutesAsyncClient(
    credentials=Credentials(
      token=google_routes_api_key,
    )
  )

  travel_modes = [RouteTravelMode.DRIVE]
  if include_cycling:
    travel_modes.append(RouteTravelMode.BICYCLE)
  if include_transit:
    travel_modes.append(RouteTravelMode.TRANSIT)
  if include_walking:
    travel_modes.append(RouteTravelMode.WALK)

  # Initialize and send requests
  mode_to_in_flight_requests = {
    mode: send_route_request(
      client=client,
      request=create_route_request(
        mode,
        origin,
        destination,
        departure_time=time_constraint.estimated_departure_time(),
      ),
      metadata=[FIELD_MASK_HEADER],
    )
    for mode in travel_modes
  }

  # Construct the response model
  modes_to_responses = await gather_map(mode_to_in_flight_requests)

  # Drive
  res = modes_to_responses[RouteTravelMode.DRIVE]
  route = res.routes[0]
  depart, arrive = time_constraint.resolve(timedelta(seconds=route.duration.seconds))
  drive_details = DrivingRouteDetails(
    departure_time=depart,
    arrival_time=arrive,
    distance_meters=route.distance_meters,
  )

  # Bike
  bike_details = None
  if RouteTravelMode.BICYCLE in modes_to_responses:
    res = modes_to_responses[RouteTravelMode.BICYCLE]
    route = res.routes[0]
    depart, arrive = time_constraint.resolve(timedelta(seconds=route.duration.seconds))
    bike_details = CyclingRouteDetails(
      departure_time=depart,
      arrival_time=arrive,  # type: ignore
      distance_meters=route.distance_meters,
    )

  # Transit
  transit_details = None
  if RouteTravelMode.TRANSIT in modes_to_responses:
    res = modes_to_responses[RouteTravelMode.TRANSIT]
    route = res.routes[0]
    depart, arrive = time_constraint.resolve(timedelta(seconds=route.duration.seconds))
    transit_details = RouteDetails(
      departure_time=depart,  # type: ignore
      arrival_time=arrive,  # type: ignore
      distance_meters=route.distance_meters,
    )

  # Walk
  walking_details = None
  if RouteTravelMode.WALK in modes_to_responses:
    res = modes_to_responses[RouteTravelMode.WALK]
    route = res.routes[0]
    depart, arrive = time_constraint.resolve(timedelta(seconds=route.duration.seconds))
    walking_details = RouteDetails(
      departure_time=depart,  # type: ignore
      arrival_time=arrive,  # type: ignore
      distance_meters=route.distance_meters,
    )

  return RouteDetailsByMode(
    origin=origin,
    destination=destination,
    bike=bike_details,
    drive=drive_details,
    transit=transit_details,
    walk=walking_details,
  )


FIELD_MASK_HEADER = (
  "x-goog-fieldmask",
  "routes.distanceMeters,routes.duration,routes.description,"
  "routes.travel_advisory.fuel_consumption_microliters,"
  "geocoding_results",
)


def create_route_request(
  mode: RouteTravelMode,
  origin: Location,
  destination: Location,
  departure_time: datetime,
) -> ComputeRoutesRequest:
  posix = departure_time.timestamp()
  seconds = int(posix)
  nanos = int((posix % 1) * 1e6)
  departure_timestamp = Timestamp(seconds=seconds, nanos=nanos)

  return ComputeRoutesRequest(
    origin=origin.as_waypoint(),
    destination=destination.as_waypoint(),
    departure_time=departure_timestamp,
    travel_mode=mode,
    routing_preference=RoutingPreference.TRAFFIC_AWARE if mode == RouteTravelMode.DRIVE else None,
  )


# @google.api_core.retry.AsyncRetry(predicate=lambda err: True)
def send_route_request(
  client: RoutesAsyncClient,
  request: ComputeRoutesRequest,
  metadata: Sequence[tuple[str, str | bytes]],
) -> CoroutineType[Any, Any, ComputeRoutesResponse]:
  return client.compute_routes(request=request, metadata=metadata)
