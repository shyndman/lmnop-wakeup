from collections.abc import Mapping
from datetime import datetime
from typing import Any, TypeVar

from pydantic import AwareDatetime, BaseModel, computed_field

T = TypeVar("T", bound="Currently")


class Currently(BaseModel):
  """A block containing the current weather for the requested location.

  Attributes:
      time (None | int): The current time in UNIX format. Example: 1746032940.
      summary (None | str): A human-readable summary of the current weather.
          Example: Mostly Cloudy.
      icon (None | str): An icon representing the current weather. Example: partly-cloudy-day.
      nearest_storm_distance (None | float): The distance to the nearest storm in kilometers.
          Example: 30.07.
      nearest_storm_bearing (None | int): The direction to the nearest storm in degrees.
      precip_intensity (None | float): The intensity of liquid water equivalent precipitation
          in millimeters per hour.
      precip_probability (None | float): The probability of precipitation occurring. Example: 0.14.
      precip_intensity_error (None | float): The standard deviation of the precipitation
          intensity. Example: 0.41.
      precip_type (None | str): The type of precipitation occurring. Example: none.
      temperature (None | float): The air temperature. Example: 23.36.
      apparent_temperature (None | float): The apparent temperature (feels like). Example: 23.16.
      dew_point (None | float): The dew point temperature. Example: 19.38.
      humidity (None | float): The relative humidity. Example: 0.8.
      pressure (None | float): The sea-level pressure in hectopascals. Example: 1016.12.
      wind_speed (None | float): The wind speed. Example: 19.17.
      wind_gust (None | float): The wind gust speed. Example: 29.97.
      wind_bearing (None | int): The direction of the wind in degrees. Example: 156.
      cloud_cover (None | float): The fraction of the sky covered by clouds. Example: 0.72.
      uv_index (None | float): The UV index. Example: 4.34.
      visibility (None | float): The visibility in kilometers. Example: 14.75.
      ozone (None | float): The ozone concentration in Dobson units. Example: 304.4.
      smoke (None | float): The amount of near-surface smoke in ug/m^3. Only returned when
          version>2. Example: 0.35.
      fire_index (None | float): The Fosburg fire index. Only returned when version>2.
          Example: 9.72.
      feels_like (None | float): The apparent temperature reported by NBM and gfs. Only returned
          when version>2. Example: 24.01.
      current_day_ice (None | float): The ice precipitation that has accumulated so far during
          the day, from midnight until the forecast request time. Only returned when version>2.
      current_day_liquid (None | float): The liquid precipitation that has accumulated so far
          during the day, from midnight until the forecast request time. Only returned when
          version>2. Example: 0.0508.
      current_day_snow (None | float): The snow precipitation that has accumulated so far during
          the day, from midnight until the forecast request time. Only returned when version>2.
  """

  time: None | int = None
  summary: None | str = None
  icon: None | str = None
  nearest_storm_distance: None | float = None
  nearest_storm_bearing: None | int = None
  precip_intensity: None | float = None
  precip_probability: None | float = None
  precip_intensity_error: None | float = None
  precip_type: None | str = None
  temperature: None | float = None
  apparent_temperature: None | float = None
  dew_point: None | float = None
  humidity: None | float = None
  pressure: None | float = None
  wind_speed: None | float = None
  wind_gust: None | float = None
  wind_bearing: None | int = None
  cloud_cover: None | float = None
  uv_index: None | float = None
  visibility: None | float = None
  ozone: None | float = None
  smoke: None | float = None
  fire_index: None | float = None
  feels_like: None | float = None
  current_day_ice: None | float = None
  current_day_liquid: None | float = None
  current_day_snow: None | float = None

  @computed_field
  @property
  def local_time(self) -> AwareDatetime | None:
    if self.time is None:
      return None
    else:
      return datetime.fromtimestamp(
        self.time,
      ).astimezone()

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
    field_dict.update({})
    if time is not None:
      field_dict["time"] = time
    if summary is not None:
      field_dict["summary"] = summary
    if icon is not None:
      field_dict["icon"] = icon
    if nearest_storm_distance is not None:
      field_dict["nearestStormDistance"] = nearest_storm_distance
    if nearest_storm_bearing is not None:
      field_dict["nearestStormBearing"] = nearest_storm_bearing
    if precip_intensity is not None:
      field_dict["precipIntensity"] = precip_intensity
    if precip_probability is not None:
      field_dict["precipProbability"] = precip_probability
    if precip_intensity_error is not None:
      field_dict["precipIntensityError"] = precip_intensity_error
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
    if fire_index is not None:
      field_dict["fireIndex"] = fire_index
    if feels_like is not None:
      field_dict["feelsLike"] = feels_like
    if current_day_ice is not None:
      field_dict["currentDayIce"] = current_day_ice
    if current_day_liquid is not None:
      field_dict["currentDayLiquid"] = current_day_liquid
    if current_day_snow is not None:
      field_dict["currentDaySnow"] = current_day_snow

    return field_dict

  @classmethod
  def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
    d = dict(src_dict)
    time = d.pop("time", None)

    summary = d.pop("summary", None)

    icon = d.pop("icon", None)

    nearest_storm_distance = d.pop("nearestStormDistance", None)

    nearest_storm_bearing = d.pop("nearestStormBearing", None)

    precip_intensity = d.pop("precipIntensity", None)

    precip_probability = d.pop("precipProbability", None)

    precip_intensity_error = d.pop("precipIntensityError", None)

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

    fire_index = d.pop("fireIndex", None)

    feels_like = d.pop("feelsLike", None)

    current_day_ice = d.pop("currentDayIce", None)

    current_day_liquid = d.pop("currentDayLiquid", None)

    current_day_snow = d.pop("currentDaySnow", None)

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

    return currently
