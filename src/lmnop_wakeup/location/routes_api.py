from collections.abc import Sequence
from datetime import datetime, timedelta
from types import CoroutineType
from typing import Any

import structlog
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
from haversine import Unit
from haversine.haversine import haversine
from langgraph.func import task
from pydantic import BaseModel, computed_field

from lmnop_wakeup.core.tracing import trace

from ..core.asyncio import gather_map
from ..core.cache import cached
from ..env import ApiKey, get_google_cloud_api_key
from .model import CoordinateLocation

logger = structlog.get_logger()


class RouteDetails(BaseModel):
  departure_time: datetime
  arrival_time: datetime
  distance_meters: int

  @computed_field
  @property
  def duration(self) -> timedelta:
    return self.arrival_time - self.departure_time


CALORIES_CONSUMED_PER_KM = 23


class NoRouteFound(BaseModel):
  pass


class ZeroDistanceRoute(BaseModel):
  """Returned when the origin location is equal to the destination"""

  pass


class CyclingRouteDetails(RouteDetails):
  @property
  def calories_consumed(self):
    """Get the projected calorie consumption for the bike ride."""
    return CALORIES_CONSUMED_PER_KM * self.distance_meters / 1000


class DrivingRouteDetails(RouteDetails):
  pass


class RouteDetailsByMode(BaseModel):
  origin: CoordinateLocation
  destination: CoordinateLocation

  bike: CyclingRouteDetails | ZeroDistanceRoute | NoRouteFound | None
  drive: DrivingRouteDetails | ZeroDistanceRoute | NoRouteFound
  """We will always have a driving route, and if we don't, the tool will fail"""

  transit: RouteDetails | ZeroDistanceRoute | NoRouteFound | None
  walk: RouteDetails | ZeroDistanceRoute | NoRouteFound | None


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


@trace(name="api: compute_route_durations")
@cached(ttl=60 * 60 * 4)
@task()
async def compute_route_durations(
  origin: CoordinateLocation,
  destination: CoordinateLocation,
  time_constraint: TimeConstraint,
  include_cycling: bool,
  include_transit: bool,
  include_walking: bool,
  google_routes_api_key: ApiKey | None = None,
) -> RouteDetailsByMode:
  logger.debug(
    f"Computing route durations for origin={origin}, destination={destination}, "
    f"time_constraint={time_constraint}, include_cycling={include_cycling}, "
    f"include_transit={include_transit}, include_walking={include_walking}"
  )

  # Do a quick check for (near-)equality of the origin and destination
  if haversine(origin.latlng_tuple, destination.latlng_tuple, unit=Unit.METERS) < 0.1:
    return RouteDetailsByMode(
      origin=origin,
      destination=destination,
      bike=ZeroDistanceRoute(),
      drive=ZeroDistanceRoute(),
      transit=ZeroDistanceRoute(),
      walk=ZeroDistanceRoute(),
    )

  # Create a client
  client = routing_v2.RoutesAsyncClient(
    credentials=Credentials(
      token=google_routes_api_key or get_google_cloud_api_key(),
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
  logger.debug(f"Sending route requests for modes: {travel_modes}")

  # Construct the response model
  modes_to_responses = await gather_map(mode_to_in_flight_requests)
  logger.debug(f"Received responses for route requests: {modes_to_responses}")

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
    if len(res.routes) == 0:
      bike_details = NoRouteFound()
    else:
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
    if len(res.routes) == 0:
      transit_details = NoRouteFound()
    else:
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
    if len(res.routes) == 0:
      walking_details = NoRouteFound()
    else:
      route = res.routes[0]
      depart, arrive = time_constraint.resolve(timedelta(seconds=route.duration.seconds))
      walking_details = RouteDetails(
        departure_time=depart,  # type: ignore
        arrival_time=arrive,  # type: ignore
        distance_meters=route.distance_meters,
      )

  route_details_by_mode = RouteDetailsByMode(
    origin=origin,
    destination=destination,
    bike=bike_details,
    drive=drive_details,
    transit=transit_details,
    walk=walking_details,
  )
  logger.debug(f"Returning RouteDetailsByMode: {route_details_by_mode}")
  return route_details_by_mode


FIELD_MASK_HEADER = (
  "x-goog-fieldmask",
  "routes.distanceMeters,routes.duration,routes.description,"
  "routes.travel_advisory.fuel_consumption_microliters,"
  "geocoding_results",
)


def create_route_request(
  mode: RouteTravelMode,
  origin: CoordinateLocation,
  destination: CoordinateLocation,
  departure_time: datetime,
) -> ComputeRoutesRequest:
  logger.debug(
    f"Creating route request for mode={mode}, origin={origin}, destination={destination}, "
    f"departure_time={departure_time}",
  )
  posix = departure_time.timestamp()
  seconds = int(posix)
  nanos = int((posix % 1) * 1e6)
  departure_timestamp = Timestamp(seconds=seconds, nanos=nanos)

  route_request = ComputeRoutesRequest(
    origin=origin.as_waypoint(),
    destination=destination.as_waypoint(),
    departure_time=departure_timestamp,
    travel_mode=mode,
    routing_preference=RoutingPreference.TRAFFIC_AWARE if mode == RouteTravelMode.DRIVE else None,
  )
  logger.debug(f"Returning ComputeRoutesRequest for mode {mode}")
  return route_request


# @google.api_core.retry.AsyncRetry(predicate=lambda err: True)
def send_route_request(
  client: RoutesAsyncClient,
  request: ComputeRoutesRequest,
  metadata: Sequence[tuple[str, str | bytes]],
) -> CoroutineType[Any, Any, ComputeRoutesResponse]:
  logger.debug(f"Sending route request for mode: {request.travel_mode}")
  return client.compute_routes(request=request, metadata=metadata)
