from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="HourlyDataItem")


@_attrs_define
class HourlyDataItem:
  """
  Attributes:
      time (Unset | int): The time of the data point in UNIX format. Example: 1746032400.
      summary (Unset | str): A summary of the weather. Example: Mostly Cloudy.
      icon (Unset | str): An icon representing the weather. Example: partly-cloudy-day.
      precip_intensity (Unset | float): The intensity of precipitation.
      precip_probability (Unset | float): The probability of precipitation. Example: 0.14.
      precip_intensity_error (Unset | float): The standard deviation of the precipitation
          intensity. Example: 0.4091.
      precip_accumulation (Unset | float): The total amount of precipitation.
      precip_type (Unset | str): The type of precipitation occurring. Example: rain.
      temperature (Unset | float): The air temperature. Example: 23.73.
      apparent_temperature (Unset | float): The apparent temperature (feels like). Example: 24.73.
      dew_point (Unset | float): The dew point temperature. Example: 19.1.
      humidity (Unset | float): The relative humidity. Example: 0.75.
      pressure (Unset | float): The air pressure. Example: 1016.32.
      wind_speed (Unset | float): The wind speed. Example: 11.52.
      wind_gust (Unset | float): The wind gust speed. Example: 21.6.
      wind_bearing (Unset | float): The direction of the wind in degrees. Example: 160.
      cloud_cover (Unset | float): The fraction of the sky covered by clouds. Example: 0.74.
      uv_index (Unset | float): The UV index. Example: 4.11.
      visibility (Unset | float): The visibility in kilometers. Example: 14.48.
      ozone (Unset | float): The ozone concentration in Dobson units. Example: 304.38.
      smoke (Unset | float): The amount of near-surface smoke in ug/m3. Only returned when
          version>2. Example: 0.32.
      liquid_accumulation (Unset | float): The amount of liquid precipitation expected. Only
          returned when version>2.
      snow_accumulation (Unset | float): The amount of snow precipitation expected. Only
          returned when version>2.
      ice_accumulation (Unset | float): The amount of ice precipitation expected. Only
          returned when version>2.
      nearest_storm_distance (Unset | float): The distance to the nearest storm. Example: 35.59.
      nearest_storm_bearing (Unset | float): The direction to the nearest storm. Example: 45.
      fire_index (Unset | float): The Fosburg fire index. Only returned when version>2.
          Example: 9.39.
      feels_like (Unset | float): The apparent temperature reported by NBM and gfs. Only
          returned when version>2. Example: 23.79.
  """

  time: Unset | int = _attrs_field(default=UNSET, init=True)
  summary: Unset | str = UNSET
  icon: Unset | str = UNSET
  precip_intensity: Unset | float = UNSET
  precip_probability: Unset | float = UNSET
  precip_intensity_error: Unset | float = UNSET
  precip_accumulation: Unset | float = UNSET
  precip_type: Unset | str = UNSET
  temperature: Unset | float = UNSET
  apparent_temperature: Unset | float = UNSET
  dew_point: Unset | float = UNSET
  humidity: Unset | float = UNSET
  pressure: Unset | float = UNSET
  wind_speed: Unset | float = UNSET
  wind_gust: Unset | float = UNSET
  wind_bearing: Unset | float = UNSET
  cloud_cover: Unset | float = UNSET
  uv_index: Unset | float = UNSET
  visibility: Unset | float = UNSET
  ozone: Unset | float = UNSET
  smoke: Unset | float = UNSET
  liquid_accumulation: Unset | float = UNSET
  snow_accumulation: Unset | float = UNSET
  ice_accumulation: Unset | float = UNSET
  nearest_storm_distance: Unset | float = UNSET
  nearest_storm_bearing: Unset | float = UNSET
  fire_index: Unset | float = UNSET
  feels_like: Unset | float = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    time = self.time

    summary = self.summary

    icon = self.icon

    precip_intensity = self.precip_intensity

    precip_probability = self.precip_probability

    precip_intensity_error = self.precip_intensity_error

    precip_accumulation = self.precip_accumulation

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

    liquid_accumulation = self.liquid_accumulation

    snow_accumulation = self.snow_accumulation

    ice_accumulation = self.ice_accumulation

    nearest_storm_distance = self.nearest_storm_distance

    nearest_storm_bearing = self.nearest_storm_bearing

    fire_index = self.fire_index

    feels_like = self.feels_like

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if time is not UNSET:
      field_dict["time"] = time
    if summary is not UNSET:
      field_dict["summary"] = summary
    if icon is not UNSET:
      field_dict["icon"] = icon
    if precip_intensity is not UNSET:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not UNSET:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not UNSET:
      field_dict["precipIntensityError"] = precip_intensity_error
    if precip_accumulation is not UNSET:
      field_dict["precipAccumulation"] = precip_accumulation
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
    if liquid_accumulation is not UNSET:
      field_dict["liquidAccumulation"] = liquid_accumulation
    if snow_accumulation is not UNSET:
      field_dict["snowAccumulation"] = snow_accumulation
    if ice_accumulation is not UNSET:
      field_dict["iceAccumulation"] = ice_accumulation
    if nearest_storm_distance is not UNSET:
      field_dict["nearestStormDistance"] = nearest_storm_distance
    if nearest_storm_bearing is not UNSET:
      field_dict["nearestStormBearing"] = nearest_storm_bearing
    if fire_index is not UNSET:
      field_dict["fireIndex"] = fire_index
    if feels_like is not UNSET:
      field_dict["feelsLike"] = feels_like

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", UNSET)

    summary = d.pop("summary", UNSET)

    icon = d.pop("icon", UNSET)

    precip_intensity = d.pop("precipIntensity", UNSET)

    precip_probability = d.pop("precipProbability", UNSET)

    precip_intensity_error = d.pop("precipIntensityError", UNSET)

    precip_accumulation = d.pop("precipAccumulation", UNSET)

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

    liquid_accumulation = d.pop("liquidAccumulation", UNSET)

    snow_accumulation = d.pop("snowAccumulation", UNSET)

    ice_accumulation = d.pop("iceAccumulation", UNSET)

    nearest_storm_distance = d.pop("nearestStormDistance", UNSET)

    nearest_storm_bearing = d.pop("nearestStormBearing", UNSET)

    fire_index = d.pop("fireIndex", UNSET)

    feels_like = d.pop("feelsLike", UNSET)

    hourly_data_item = cls(
      time=time,
      summary=summary,
      icon=icon,
      precip_intensity=precip_intensity,
      precip_probability=precip_probability,
      precip_intensity_error=precip_intensity_error,
      precip_accumulation=precip_accumulation,
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
      liquid_accumulation=liquid_accumulation,
      snow_accumulation=snow_accumulation,
      ice_accumulation=ice_accumulation,
      nearest_storm_distance=nearest_storm_distance,
      nearest_storm_bearing=nearest_storm_bearing,
      fire_index=fire_index,
      feels_like=feels_like,
    )

    hourly_data_item.additional_properties = d
    return hourly_data_item

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
