from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import field as _attrs_field
from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="HourlyDataItem")


class HourlyDataItem(BaseModel):
  """Represents the forecast for a single hour."""

  model_config = ConfigDict()

  time: None | int = _attrs_field(default=None, init=True)
  """The time of the data point in UNIX format. Example: 1746032400."""
  summary: None | str = None
  """A summary of the weather. Example: Mostly Cloudy."""
  icon: None | str = None
  """An icon representing the weather. Example: partly-cloudy-day."""
  precip_intensity: None | float = None
  """The intensity of precipitation."""
  precip_probability: None | float = None
  """The probability of precipitation. Example: 0.14."""
  precip_intensity_error: None | float = None
  """The standard deviation of the precipitation
  intensity. Example: 0.4091."""
  precip_accumulation: None | float = None
  """The total amount of precipitation."""
  precip_type: None | str = None
  """The type of precipitation occurring. Example: rain."""
  temperature: None | float = None
  """The air temperature. Example: 23.73."""
  apparent_temperature: None | float = None
  """The apparent temperature (feels like). Example: 24.73."""
  dew_point: None | float = None
  """The dew point temperature. Example: 19.1."""
  humidity: None | float = None
  """The relative humidity. Example: 0.75."""
  pressure: None | float = None
  """The air pressure. Example: 1016.32."""
  wind_speed: None | float = None
  """The wind speed. Example: 11.52."""
  wind_gust: None | float = None
  """The wind gust speed. Example: 21.6."""
  wind_bearing: None | float = None
  """The direction of the wind in degrees. Example: 160."""
  cloud_cover: None | float = None
  """The fraction of the sky covered by clouds. Example: 0.74."""
  uv_index: None | float = None
  """The UV index. Example: 4.11."""
  visibility: None | float = None
  """The visibility in kilometers. Example: 14.48."""
  ozone: None | float = None
  """The ozone concentration in Dobson units. Example: 304.38."""
  smoke: None | float = None
  """The amount of near-surface smoke in ug/m3. Only returned when
  version>2. Example: 0.32."""
  liquid_accumulation: None | float = None
  """The amount of liquid precipitation expected. Only
  returned when version>2."""
  snow_accumulation: None | float = None
  """The amount of snow precipitation expected. Only
  returned when version>2."""
  ice_accumulation: None | float = None
  """The amount of ice precipitation expected. Only
  returned when version>2."""
  nearest_storm_distance: None | float = None
  """The distance to the nearest storm. Example: 35.59."""
  nearest_storm_bearing: None | float = None
  """The direction to the nearest storm. Example: 45."""
  fire_index: None | float = None
  """The Fosburg fire index. Only returned when version>2.
  Example: 9.39."""
  feels_like: None | float = None
  """The apparent temperature reported by NBM and gfs. Only
  returned when version>2. Example: 23.79."""
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

    if time is not None:
      field_dict["time"] = time
    if summary is not None:
      field_dict["summary"] = summary
    if icon is not None:
      field_dict["icon"] = icon
    if precip_intensity is not None:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not None:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not None:
      field_dict["precipIntensityError"] = precip_intensity_error
    if precip_accumulation is not None:
      field_dict["precipAccumulation"] = precip_accumulation
    if precip_type is not None:
      field_dict["precipType"] = precip_type
    if temperature is not None:
      field_dict["temperature"] = temperature
    if apparent_temperature is not None:
      field_dict["apparentTemperature"] = apparent_temperature
    if dew_point is not None:
      field_dict["dewPoint"] = dew_point
    if humidity is not None:
      field_dict["humidity"] = humidity
    if pressure is not None:
      field_dict["pressure"] = pressure
    if wind_speed is not None:
      field_dict["windSpeed"] = wind_speed
    if wind_gust is not None:
      field_dict["windGust"] = wind_gust
    if wind_bearing is not None:
      field_dict["windBearing"] = wind_bearing
    if cloud_cover is not None:
      field_dict["cloudCover"] = cloud_cover
    if uv_index is not None:
      field_dict["uvIndex"] = uv_index
    if visibility is not None:
      field_dict["visibility"] = visibility
    if ozone is not None:
      field_dict["ozone"] = ozone
    if smoke is not None:
      field_dict["smoke"] = smoke
    if liquid_accumulation is not None:
      field_dict["liquidAccumulation"] = liquid_accumulation
    if snow_accumulation is not None:
      field_dict["snowAccumulation"] = snow_accumulation
    if ice_accumulation is not None:
      field_dict["iceAccumulation"] = ice_accumulation
    if nearest_storm_distance is not None:
      field_dict["nearestStormDistance"] = nearest_storm_distance
    if nearest_storm_bearing is not None:
      field_dict["nearestStormBearing"] = nearest_storm_bearing
    if fire_index is not None:
      field_dict["fireIndex"] = fire_index
    if feels_like is not None:
      field_dict["feelsLike"] = feels_like

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", None)
    summary = d.pop("summary", None)
    icon = d.pop("icon", None)
    precip_intensity = d.pop("precipIntensity", None)
    precip_probability = d.pop("precipProbability", None)
    precip_intensity_error = d.pop("precipIntensityError", None)
    precip_accumulation = d.pop("precipAccumulation", None)
    precip_type = d.pop("precipType", None)
    temperature = d.pop("temperature", None)
    apparent_temperature = d.pop("apparentTemperature", None)
    dew_point = d.pop("dewPoint", None)
    humidity = d.pop("humidity", None)
    pressure = d.pop("pressure", None)
    wind_speed = d.pop("windSpeed", None)
    wind_gust = d.pop("windGust", None)
    wind_bearing = d.pop("windBearing", None)
    cloud_cover = d.pop("cloudCover", None)
    uv_index = d.pop("uvIndex", None)
    visibility = d.pop("visibility", None)
    ozone = d.pop("ozone", None)
    smoke = d.pop("smoke", None)
    liquid_accumulation = d.pop("liquidAccumulation", None)
    snow_accumulation = d.pop("snowAccumulation", None)
    ice_accumulation = d.pop("iceAccumulation", None)
    nearest_storm_distance = d.pop("nearestStormDistance", None)
    nearest_storm_bearing = d.pop("nearestStormBearing", None)
    fire_index = d.pop("fireIndex", None)
    feels_like = d.pop("feelsLike", None)

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
