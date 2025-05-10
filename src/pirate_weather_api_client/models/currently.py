from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from pydantic import BaseModel

from ..types import UNSET, Unset

T = TypeVar("T", bound="Currently")


@_attrs_define
class Currently(BaseModel):
  """A block containing the current weather for the requested location.

  Attributes:
      time (Unset | int): The current time in UNIX format. Example: 1746032940.
      summary (Unset | str): A human-readable summary of the current weather.
          Example: Mostly Cloudy.
      icon (Unset | str): An icon representing the current weather. Example: partly-cloudy-day.
      nearest_storm_distance (Unset | float): The distance to the nearest storm in kilometers.
          Example: 30.07.
      nearest_storm_bearing (Unset | int): The direction to the nearest storm in degrees.
      precip_intensity (Unset | float): The intensity of liquid water equivalent precipitation
          in millimeters per hour.
      precip_probability (Unset | float): The probability of precipitation occurring. Example: 0.14.
      precip_intensity_error (Unset | float): The standard deviation of the precipitation
          intensity. Example: 0.41.
      precip_type (Unset | str): The type of precipitation occurring. Example: none.
      temperature (Unset | float): The air temperature. Example: 23.36.
      apparent_temperature (Unset | float): The apparent temperature (feels like). Example: 23.16.
      dew_point (Unset | float): The dew point temperature. Example: 19.38.
      humidity (Unset | float): The relative humidity. Example: 0.8.
      pressure (Unset | float): The sea-level pressure in hectopascals. Example: 1016.12.
      wind_speed (Unset | float): The wind speed. Example: 19.17.
      wind_gust (Unset | float): The wind gust speed. Example: 29.97.
      wind_bearing (Unset | int): The direction of the wind in degrees. Example: 156.
      cloud_cover (Unset | float): The fraction of the sky covered by clouds. Example: 0.72.
      uv_index (Unset | float): The UV index. Example: 4.34.
      visibility (Unset | float): The visibility in kilometers. Example: 14.75.
      ozone (Unset | float): The ozone concentration in Dobson units. Example: 304.4.
      smoke (Unset | float): The amount of near-surface smoke in ug/m^3. Only returned when
          version>2. Example: 0.35.
      fire_index (Unset | float): The Fosburg fire index. Only returned when version>2.
          Example: 9.72.
      feels_like (Unset | float): The apparent temperature reported by NBM and gfs. Only returned
          when version>2. Example: 24.01.
      current_day_ice (Unset | float): The ice precipitation that has accumulated so far during
          the day, from midnight until the forecast request time. Only returned when version>2.
      current_day_liquid (Unset | float): The liquid precipitation that has accumulated so far
          during the day, from midnight until the forecast request time. Only returned when
          version>2. Example: 0.0508.
      current_day_snow (Unset | float): The snow precipitation that has accumulated so far during
          the day, from midnight until the forecast request time. Only returned when version>2.
  """

  time: Unset | int = UNSET
  summary: Unset | str = UNSET
  icon: Unset | str = UNSET
  nearest_storm_distance: Unset | float = UNSET
  nearest_storm_bearing: Unset | int = UNSET
  precip_intensity: Unset | float = UNSET
  precip_probability: Unset | float = UNSET
  precip_intensity_error: Unset | float = UNSET
  precip_type: Unset | str = UNSET
  temperature: Unset | float = UNSET
  apparent_temperature: Unset | float = UNSET
  dew_point: Unset | float = UNSET
  humidity: Unset | float = UNSET
  pressure: Unset | float = UNSET
  wind_speed: Unset | float = UNSET
  wind_gust: Unset | float = UNSET
  wind_bearing: Unset | int = UNSET
  cloud_cover: Unset | float = UNSET
  uv_index: Unset | float = UNSET
  visibility: Unset | float = UNSET
  ozone: Unset | float = UNSET
  smoke: Unset | float = UNSET
  fire_index: Unset | float = UNSET
  feels_like: Unset | float = UNSET
  current_day_ice: Unset | float = UNSET
  current_day_liquid: Unset | float = UNSET
  current_day_snow: Unset | float = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    time = self.time

    summary = self.summary

    icon = self.icon

    nearest_storm_distance = self.nearest_storm_distance

    nearest_storm_bearing = self.nearest_storm_bearing

    precip_intensity = self.precip_intensity

    precip_probability = self.precip_probability

    precip_intensity_error = self.precip_intensity_error

    precip_type = self.precip_type

    temperature = self.temperature

    apparent_temperature = self.apparent_temperature

    dew_point = self.dew_point

    humidity = self.humidity

    pressure = self.pressure

    wind_speed = self.wind_speed

    wind_gust = self.wind_gust

    wind_bearing = self.wind_bearing

    cloud_cover = self.cloud_cover

    uv_index = self.uv_index

    visibility = self.visibility

    ozone = self.ozone

    smoke = self.smoke

    fire_index = self.fire_index

    feels_like = self.feels_like

    current_day_ice = self.current_day_ice

    current_day_liquid = self.current_day_liquid

    current_day_snow = self.current_day_snow

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if time is not UNSET:
      field_dict["time"] = time
    if summary is not UNSET:
      field_dict["summary"] = summary
    if icon is not UNSET:
      field_dict["icon"] = icon
    if nearest_storm_distance is not UNSET:
      field_dict["nearestStormDistance"] = nearest_storm_distance
    if nearest_storm_bearing is not UNSET:
      field_dict["nearestStormBearing"] = nearest_storm_bearing
    if precip_intensity is not UNSET:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not UNSET:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not UNSET:
      field_dict["precipIntensityError"] = precip_intensity_error
    if precip_type is not UNSET:
      field_dict["precipType"] = precip_type
    if temperature is not UNSET:
      field_dict["temperature"] = temperature
    if apparent_temperature is not UNSET:
      field_dict["apparentTemperature"] = apparent_temperature
    if dew_point is not UNSET:
      field_dict["dewPoint"] = dew_point
    if humidity is not UNSET:
      field_dict["humidity"] = humidity
    if pressure is not UNSET:
      field_dict["pressure"] = pressure
    if wind_speed is not UNSET:
      field_dict["windSpeed"] = wind_speed
    if wind_gust is not UNSET:
      field_dict["windGust"] = wind_gust
    if wind_bearing is not UNSET:
      field_dict["windBearing"] = wind_bearing
    if cloud_cover is not UNSET:
      field_dict["cloudCover"] = cloud_cover
    if uv_index is not UNSET:
      field_dict["uvIndex"] = uv_index
    if visibility is not UNSET:
      field_dict["visibility"] = visibility
    if ozone is not UNSET:
      field_dict["ozone"] = ozone
    if smoke is not UNSET:
      field_dict["smoke"] = smoke
    if fire_index is not UNSET:
      field_dict["fireIndex"] = fire_index
    if feels_like is not UNSET:
      field_dict["feelsLike"] = feels_like
    if current_day_ice is not UNSET:
      field_dict["currentDayIce"] = current_day_ice
    if current_day_liquid is not UNSET:
      field_dict["currentDayLiquid"] = current_day_liquid
    if current_day_snow is not UNSET:
      field_dict["currentDaySnow"] = current_day_snow

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", UNSET)

    summary = d.pop("summary", UNSET)

    icon = d.pop("icon", UNSET)

    nearest_storm_distance = d.pop("nearestStormDistance", UNSET)

    nearest_storm_bearing = d.pop("nearestStormBearing", UNSET)

    precip_intensity = d.pop("precipIntensity", UNSET)

    precip_probability = d.pop("precipProbability", UNSET)

    precip_intensity_error = d.pop("precipIntensityError", UNSET)

    precip_type = d.pop("precipType", UNSET)

    temperature = d.pop("temperature", UNSET)

    apparent_temperature = d.pop("apparentTemperature", UNSET)

    dew_point = d.pop("dewPoint", UNSET)

    humidity = d.pop("humidity", UNSET)

    pressure = d.pop("pressure", UNSET)

    wind_speed = d.pop("windSpeed", UNSET)

    wind_gust = d.pop("windGust", UNSET)

    wind_bearing = d.pop("windBearing", UNSET)

    cloud_cover = d.pop("cloudCover", UNSET)

    uv_index = d.pop("uvIndex", UNSET)

    visibility = d.pop("visibility", UNSET)

    ozone = d.pop("ozone", UNSET)

    smoke = d.pop("smoke", UNSET)

    fire_index = d.pop("fireIndex", UNSET)

    feels_like = d.pop("feelsLike", UNSET)

    current_day_ice = d.pop("currentDayIce", UNSET)

    current_day_liquid = d.pop("currentDayLiquid", UNSET)

    current_day_snow = d.pop("currentDaySnow", UNSET)

    currently = cls(
      time=time,
      summary=summary,
      icon=icon,
      nearest_storm_distance=nearest_storm_distance,
      nearest_storm_bearing=nearest_storm_bearing,
      precip_intensity=precip_intensity,
      precip_probability=precip_probability,
      precip_intensity_error=precip_intensity_error,
      precip_type=precip_type,
      temperature=temperature,
      apparent_temperature=apparent_temperature,
      dew_point=dew_point,
      humidity=humidity,
      pressure=pressure,
      wind_speed=wind_speed,
      wind_gust=wind_gust,
      wind_bearing=wind_bearing,
      cloud_cover=cloud_cover,
      uv_index=uv_index,
      visibility=visibility,
      ozone=ozone,
      smoke=smoke,
      fire_index=fire_index,
      feels_like=feels_like,
      current_day_ice=current_day_ice,
      current_day_liquid=current_day_liquid,
      current_day_snow=current_day_snow,
    )

    currently.additional_properties = d
    return currently

  @property
  def additional_keys(self) -> list[str]:
    return list(self.additional_properties.keys())

  def __getitem__(self, key: str) -> Any:
    return self.additional_properties[key]

  def __setitem__(self, key: str, value: Any) -> None:
    self.additional_properties[key] = value

  def __delitem__(self, key: str) -> None:
    del self.additional_properties[key]

  def __contains__(self, key: str) -> bool:
    return key in self.additional_properties
