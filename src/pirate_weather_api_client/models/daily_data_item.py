from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DailyDataItem")


@_attrs_define
class DailyDataItem:
  """
  Attributes:
      time (Unset | int): The time of the data point in UNIX format. Example: 1745989200.
      summary (Unset | str): A summary of the weather. Example: Possible light rain..
      icon (Unset | str): An icon representing the weather. Example: partly-cloudy-day.
      dawn_time (Unset | int): The time when the the sun is a specific (6 degrees) height
          above the horizon after sunrise. Only returned when version>2. Example: 1746009343.
      sunrise_time (Unset | int): The time of sunrise in UNIX format. Example: 1746011052.
      sunset_time (Unset | int): The time of sunset in UNIX format. Example: 1746060412.
      dusk_time (Unset | int): The time when the the sun is a specific (6 degrees) height above
          the horizon before sunset. Only returned when version>2. Example: 1746062127.
      moon_phase (Unset | float): The fractional lunation number for the given day. Example: 0.1.
      precip_intensity (Unset | float): The intensity of precipitation. Example: 0.0953.
      precip_intensity_max (Unset | float): The maximum intensity of precipitation. Example: 2.0322.
      precip_intensity_max_time (Unset | int): The time when the maximum precipitation intensity
          occurs in UNIX format. Example: 1746046800.
      precip_probability (Unset | float): The probability of precipitation. Example: 0.23.
      precip_accumulation (Unset | float): The total amount of precipitation. Example: 0.2286.
      precip_type (Unset | str): The type of precipitation occurring. Example: rain.
      temperature_high (Unset | float): The daytime high temperature. Example: 26.6.
      temperature_high_time (Unset | int): The time when the high temperature occurs in UNIX
          format. Example: 1746043200.
      temperature_low (Unset | float): The overnight low temperature. Example: 18.85.
      temperature_low_time (Unset | int): The time when the low temperature occurs in UNIX
          format. Example: 1746097200.
      apparent_temperature_high (Unset | float): The apparent daytime high temperature (feels
          like). Example: 27.02.
      apparent_temperature_high_time (Unset | int): The time when the apparent high temperature
          occurs in UNIX format. Example: 1746043200.
      apparent_temperature_low (Unset | float): The apparent overnight low temperature (feels
          like). Example: 18.09.
      apparent_temperature_low_time (Unset | int): The time when the apparent low temperature
          occurs in UNIX format. Example: 1746097200.
      dew_point (Unset | float): The dew point temperature. Example: 17.79.
      humidity (Unset | float): The relative humidity. Example: 0.8.
      pressure (Unset | float): The air pressure. Example: 1014.73.
      wind_speed (Unset | float): The wind speed. Example: 9.08.
      wind_gust (Unset | float): The wind gust speed. Example: 17.95.
      wind_gust_time (Unset | int): The time when the maximum wind gust occurs in UNIX format.
          Example: 1746046800.
      wind_bearing (Unset | int): The direction of the wind in degrees. Example: 130.
      cloud_cover (Unset | float): The fraction of the sky covered by clouds. Example: 0.68.
      uv_index (Unset | float): The max UV index during that day. Example: 6.53.
      uv_index_time (Unset | int): The time when the maximum UV index occurs in UNIX format.
          Example: 1746043200.
      visibility (Unset | float): The visibility in kilometers. Example: 11.61.
      temperature_min (Unset | float): The minimum temperature. Example: 17.54.
      temperature_min_time (Unset | int): The time when the minimum temperature occurs in
          UNIX format. Example: 1746010800.
      temperature_max (Unset | float): The maximum temperature. Example: 26.6.
      temperature_max_time (Unset | int): The time when the maximum temperature occurs in UNIX
          format. Example: 1746043200.
      apparent_temperature_min (Unset | float): The minimum apparent temperature (feels like).
          Example: 18.97.
      apparent_temperature_min_time (Unset | int): The time when the minimum apparent temperature
          occurs in UNIX format. Example: 1746014400.
      apparent_temperature_max (Unset | float): The maximum apparent temperature (feels like).
          Example: 27.02.
      apparent_temperature_max_time (Unset | int): The time when the maximum apparent temperature
          occurs in UNIX format. Example: 1746043200.
      smoke_max (Unset | float): The maximum amount of near-surface smoke in kg/m^3. Only
          returned when version>2. Example: 1.76.
      smoke_max_time (Unset | int): The time when the maximum near-surface smoke occurs in
          UNIX format. Only returned when version>2. Example: 1746061200.
      liquid_accumulation (Unset | float): The amount of liquid precipitation expected.
          Only returned when version>2. Example: 0.2286.
      snow_accumulation (Unset | float): The amount of snow precipitation expected. Only returned
          when version>2.
      ice_accumulation (Unset | float): The amount of ice precipitation expected. Only returned
          when version>2.
      fire_index_max (Unset | float): The maximum Fosburg fire index. Only returned when version>2.
        Example: 16.2.
      fire_index_max_time (Unset | int): The time when the maximum Fosburg fire index occurs in
          UNIX format. Only returned when version>2. Example: 1746057600.
  """

  time: Unset | int = UNSET
  summary: Unset | str = UNSET
  icon: Unset | str = UNSET
  dawn_time: Unset | int = UNSET
  sunrise_time: Unset | int = UNSET
  sunset_time: Unset | int = UNSET
  dusk_time: Unset | int = UNSET
  moon_phase: Unset | float = UNSET
  precip_intensity: Unset | float = UNSET
  precip_intensity_max: Unset | float = UNSET
  precip_intensity_max_time: Unset | int = UNSET
  precip_probability: Unset | float = UNSET
  precip_accumulation: Unset | float = UNSET
  precip_type: Unset | str = UNSET
  temperature_high: Unset | float = UNSET
  temperature_high_time: Unset | int = UNSET
  temperature_low: Unset | float = UNSET
  temperature_low_time: Unset | int = UNSET
  apparent_temperature_high: Unset | float = UNSET
  apparent_temperature_high_time: Unset | int = UNSET
  apparent_temperature_low: Unset | float = UNSET
  apparent_temperature_low_time: Unset | int = UNSET
  dew_point: Unset | float = UNSET
  humidity: Unset | float = UNSET
  pressure: Unset | float = UNSET
  wind_speed: Unset | float = UNSET
  wind_gust: Unset | float = UNSET
  wind_gust_time: Unset | int = UNSET
  wind_bearing: Unset | int = UNSET
  cloud_cover: Unset | float = UNSET
  uv_index: Unset | float = UNSET
  uv_index_time: Unset | int = UNSET
  visibility: Unset | float = UNSET
  temperature_min: Unset | float = UNSET
  temperature_min_time: Unset | int = UNSET
  temperature_max: Unset | float = UNSET
  temperature_max_time: Unset | int = UNSET
  apparent_temperature_min: Unset | float = UNSET
  apparent_temperature_min_time: Unset | int = UNSET
  apparent_temperature_max: Unset | float = UNSET
  apparent_temperature_max_time: Unset | int = UNSET
  smoke_max: Unset | float = UNSET
  smoke_max_time: Unset | int = UNSET
  liquid_accumulation: Unset | float = UNSET
  snow_accumulation: Unset | float = UNSET
  ice_accumulation: Unset | float = UNSET
  fire_index_max: Unset | float = UNSET
  fire_index_max_time: Unset | int = UNSET
  additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

  def to_dict(self) -> dict[str, Any]:
    time = self.time

    summary = self.summary

    icon = self.icon

    dawn_time = self.dawn_time

    sunrise_time = self.sunrise_time

    sunset_time = self.sunset_time

    dusk_time = self.dusk_time

    moon_phase = self.moon_phase

    precip_intensity = self.precip_intensity

    precip_intensity_max = self.precip_intensity_max

    precip_intensity_max_time = self.precip_intensity_max_time

    precip_probability = self.precip_probability

    precip_accumulation = self.precip_accumulation

    precip_type = self.precip_type

    temperature_high = self.temperature_high

    temperature_high_time = self.temperature_high_time

    temperature_low = self.temperature_low

    temperature_low_time = self.temperature_low_time

    apparent_temperature_high = self.apparent_temperature_high

    apparent_temperature_high_time = self.apparent_temperature_high_time

    apparent_temperature_low = self.apparent_temperature_low

    apparent_temperature_low_time = self.apparent_temperature_low_time

    dew_point = self.dew_point

    humidity = self.humidity

    pressure = self.pressure

    wind_speed = self.wind_speed

    wind_gust = self.wind_gust

    wind_gust_time = self.wind_gust_time

    wind_bearing = self.wind_bearing

    cloud_cover = self.cloud_cover

    uv_index = self.uv_index

    uv_index_time = self.uv_index_time

    visibility = self.visibility

    temperature_min = self.temperature_min

    temperature_min_time = self.temperature_min_time

    temperature_max = self.temperature_max

    temperature_max_time = self.temperature_max_time

    apparent_temperature_min = self.apparent_temperature_min

    apparent_temperature_min_time = self.apparent_temperature_min_time

    apparent_temperature_max = self.apparent_temperature_max

    apparent_temperature_max_time = self.apparent_temperature_max_time

    smoke_max = self.smoke_max

    smoke_max_time = self.smoke_max_time

    liquid_accumulation = self.liquid_accumulation

    snow_accumulation = self.snow_accumulation

    ice_accumulation = self.ice_accumulation

    fire_index_max = self.fire_index_max

    fire_index_max_time = self.fire_index_max_time

    field_dict: dict[str, Any] = {}
    field_dict.update(self.additional_properties)
    field_dict.update({})
    if time is not UNSET:
      field_dict["time"] = time
    if summary is not UNSET:
      field_dict["summary"] = summary
    if icon is not UNSET:
      field_dict["icon"] = icon
    if dawn_time is not UNSET:
      field_dict["dawnTime"] = dawn_time
    if sunrise_time is not UNSET:
      field_dict["sunriseTime"] = sunrise_time
    if sunset_time is not UNSET:
      field_dict["sunsetTime"] = sunset_time
    if dusk_time is not UNSET:
      field_dict["duskTime"] = dusk_time
    if moon_phase is not UNSET:
      field_dict["moonPhase"] = moon_phase
    if precip_intensity is not UNSET:
      field_dict["precipIntensity"] = precip_intensity
    if precip_intensity_max is not UNSET:
      field_dict["precipIntensityMax"] = precip_intensity_max
    if precip_intensity_max_time is not UNSET:
      field_dict["precipIntensityMaxTime"] = precip_intensity_max_time
    if precip_probability is not UNSET:
      field_dict["precipProbability"] = precip_probability
    if precip_accumulation is not UNSET:
      field_dict["precipAccumulation"] = precip_accumulation
    if precip_type is not UNSET:
      field_dict["precipType"] = precip_type
    if temperature_high is not UNSET:
      field_dict["temperatureHigh"] = temperature_high
    if temperature_high_time is not UNSET:
      field_dict["temperatureHighTime"] = temperature_high_time
    if temperature_low is not UNSET:
      field_dict["temperatureLow"] = temperature_low
    if temperature_low_time is not UNSET:
      field_dict["temperatureLowTime"] = temperature_low_time
    if apparent_temperature_high is not UNSET:
      field_dict["apparentTemperatureHigh"] = apparent_temperature_high
    if apparent_temperature_high_time is not UNSET:
      field_dict["apparentTemperatureHighTime"] = apparent_temperature_high_time
    if apparent_temperature_low is not UNSET:
      field_dict["apparentTemperatureLow"] = apparent_temperature_low
    if apparent_temperature_low_time is not UNSET:
      field_dict["apparentTemperatureLowTime"] = apparent_temperature_low_time
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
    if wind_gust_time is not UNSET:
      field_dict["windGustTime"] = wind_gust_time
    if wind_bearing is not UNSET:
      field_dict["windBearing"] = wind_bearing
    if cloud_cover is not UNSET:
      field_dict["cloudCover"] = cloud_cover
    if uv_index is not UNSET:
      field_dict["uvIndex"] = uv_index
    if uv_index_time is not UNSET:
      field_dict["uvIndexTime"] = uv_index_time
    if visibility is not UNSET:
      field_dict["visibility"] = visibility
    if temperature_min is not UNSET:
      field_dict["temperatureMin"] = temperature_min
    if temperature_min_time is not UNSET:
      field_dict["temperatureMinTime"] = temperature_min_time
    if temperature_max is not UNSET:
      field_dict["temperatureMax"] = temperature_max
    if temperature_max_time is not UNSET:
      field_dict["temperatureMaxTime"] = temperature_max_time
    if apparent_temperature_min is not UNSET:
      field_dict["apparentTemperatureMin"] = apparent_temperature_min
    if apparent_temperature_min_time is not UNSET:
      field_dict["apparentTemperatureMinTime"] = apparent_temperature_min_time
    if apparent_temperature_max is not UNSET:
      field_dict["apparentTemperatureMax"] = apparent_temperature_max
    if apparent_temperature_max_time is not UNSET:
      field_dict["apparentTemperatureMaxTime"] = apparent_temperature_max_time
    if smoke_max is not UNSET:
      field_dict["smokeMax"] = smoke_max
    if smoke_max_time is not UNSET:
      field_dict["smokeMaxTime"] = smoke_max_time
    if liquid_accumulation is not UNSET:
      field_dict["liquidAccumulation"] = liquid_accumulation
    if snow_accumulation is not UNSET:
      field_dict["snowAccumulation"] = snow_accumulation
    if ice_accumulation is not UNSET:
      field_dict["iceAccumulation"] = ice_accumulation
    if fire_index_max is not UNSET:
      field_dict["fireIndexMax"] = fire_index_max
    if fire_index_max_time is not UNSET:
      field_dict["fireIndexMaxTime"] = fire_index_max_time

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", UNSET)

    summary = d.pop("summary", UNSET)

    icon = d.pop("icon", UNSET)

    dawn_time = d.pop("dawnTime", UNSET)

    sunrise_time = d.pop("sunriseTime", UNSET)

    sunset_time = d.pop("sunsetTime", UNSET)

    dusk_time = d.pop("duskTime", UNSET)

    moon_phase = d.pop("moonPhase", UNSET)

    precip_intensity = d.pop("precipIntensity", UNSET)

    precip_intensity_max = d.pop("precipIntensityMax", UNSET)

    precip_intensity_max_time = d.pop("precipIntensityMaxTime", UNSET)

    precip_probability = d.pop("precipProbability", UNSET)

    precip_accumulation = d.pop("precipAccumulation", UNSET)

    precip_type = d.pop("precipType", UNSET)

    temperature_high = d.pop("temperatureHigh", UNSET)

    temperature_high_time = d.pop("temperatureHighTime", UNSET)

    temperature_low = d.pop("temperatureLow", UNSET)

    temperature_low_time = d.pop("temperatureLowTime", UNSET)

    apparent_temperature_high = d.pop("apparentTemperatureHigh", UNSET)

    apparent_temperature_high_time = d.pop("apparentTemperatureHighTime", UNSET)

    apparent_temperature_low = d.pop("apparentTemperatureLow", UNSET)

    apparent_temperature_low_time = d.pop("apparentTemperatureLowTime", UNSET)

    dew_point = d.pop("dewPoint", UNSET)

    humidity = d.pop("humidity", UNSET)

    pressure = d.pop("pressure", UNSET)

    wind_speed = d.pop("windSpeed", UNSET)

    wind_gust = d.pop("windGust", UNSET)

    wind_gust_time = d.pop("windGustTime", UNSET)

    wind_bearing = d.pop("windBearing", UNSET)

    cloud_cover = d.pop("cloudCover", UNSET)

    uv_index = d.pop("uvIndex", UNSET)

    uv_index_time = d.pop("uvIndexTime", UNSET)

    visibility = d.pop("visibility", UNSET)

    temperature_min = d.pop("temperatureMin", UNSET)

    temperature_min_time = d.pop("temperatureMinTime", UNSET)

    temperature_max = d.pop("temperatureMax", UNSET)

    temperature_max_time = d.pop("temperatureMaxTime", UNSET)

    apparent_temperature_min = d.pop("apparentTemperatureMin", UNSET)

    apparent_temperature_min_time = d.pop("apparentTemperatureMinTime", UNSET)

    apparent_temperature_max = d.pop("apparentTemperatureMax", UNSET)

    apparent_temperature_max_time = d.pop("apparentTemperatureMaxTime", UNSET)

    smoke_max = d.pop("smokeMax", UNSET)

    smoke_max_time = d.pop("smokeMaxTime", UNSET)

    liquid_accumulation = d.pop("liquidAccumulation", UNSET)

    snow_accumulation = d.pop("snowAccumulation", UNSET)

    ice_accumulation = d.pop("iceAccumulation", UNSET)

    fire_index_max = d.pop("fireIndexMax", UNSET)

    fire_index_max_time = d.pop("fireIndexMaxTime", UNSET)

    daily_data_item = cls(
      time=time,
      summary=summary,
      icon=icon,
      dawn_time=dawn_time,
      sunrise_time=sunrise_time,
      sunset_time=sunset_time,
      dusk_time=dusk_time,
      moon_phase=moon_phase,
      precip_intensity=precip_intensity,
      precip_intensity_max=precip_intensity_max,
      precip_intensity_max_time=precip_intensity_max_time,
      precip_probability=precip_probability,
      precip_accumulation=precip_accumulation,
      precip_type=precip_type,
      temperature_high=temperature_high,
      temperature_high_time=temperature_high_time,
      temperature_low=temperature_low,
      temperature_low_time=temperature_low_time,
      apparent_temperature_high=apparent_temperature_high,
      apparent_temperature_high_time=apparent_temperature_high_time,
      apparent_temperature_low=apparent_temperature_low,
      apparent_temperature_low_time=apparent_temperature_low_time,
      dew_point=dew_point,
      humidity=humidity,
      pressure=pressure,
      wind_speed=wind_speed,
      wind_gust=wind_gust,
      wind_gust_time=wind_gust_time,
      wind_bearing=wind_bearing,
      cloud_cover=cloud_cover,
      uv_index=uv_index,
      uv_index_time=uv_index_time,
      visibility=visibility,
      temperature_min=temperature_min,
      temperature_min_time=temperature_min_time,
      temperature_max=temperature_max,
      temperature_max_time=temperature_max_time,
      apparent_temperature_min=apparent_temperature_min,
      apparent_temperature_min_time=apparent_temperature_min_time,
      apparent_temperature_max=apparent_temperature_max,
      apparent_temperature_max_time=apparent_temperature_max_time,
      smoke_max=smoke_max,
      smoke_max_time=smoke_max_time,
      liquid_accumulation=liquid_accumulation,
      snow_accumulation=snow_accumulation,
      ice_accumulation=ice_accumulation,
      fire_index_max=fire_index_max,
      fire_index_max_time=fire_index_max_time,
    )

    daily_data_item.additional_properties = d
    return daily_data_item

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
