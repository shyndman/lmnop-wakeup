from datetime import date, datetime
from typing import Tuple

import pandas as pd
import pvlib
from pydantic import BaseModel, Field, field_validator

# Pydantic v2 Models for Sunset Analysis


class SunsetDailyWeatherData(BaseModel):
  """Daily weather data from Open-Meteo API for sunset analysis."""

  time: list[str] = Field(..., description="Date strings in YYYY-MM-DD format")
  sunrise: list[str] = Field(..., description="Sunrise times in ISO format")
  sunset: list[str] = Field(..., description="Sunset times in ISO format")
  wind_speed_10m_max: list[float] = Field(..., description="Max wind speed")
  temperature_2m_max: list[float] = Field(..., description="Max temperature")
  temperature_2m_min: list[float] = Field(..., description="Min temperature")


class SunsetHourlyWeatherData(BaseModel):
  """Hourly weather data from Open-Meteo API for sunset analysis."""

  time: list[str] = Field(..., description="Hourly timestamps in ISO format")
  cloud_cover_low: list[float] = Field(..., description="Low cloud coverage percentage")
  cloud_cover_mid: list[float] = Field(..., description="Mid cloud coverage percentage")
  cloud_cover_high: list[float] = Field(..., description="High cloud coverage percentage")
  visibility: list[float] = Field(..., description="Visibility in meters")
  rain: list[float] = Field(default_factory=lambda: [], description="Rain in mm")
  showers: list[float] = Field(default_factory=lambda: [], description="Showers in mm")
  surface_pressure: list[float] = Field(..., description="Surface pressure in hPa")
  temperature_2m: list[float] = Field(..., description="Temperature at 2m in Celsius")

  @field_validator("rain", "showers", mode="before")
  @classmethod
  def ensure_list_length(cls, v, info):
    """Ensure rain/showers lists match time length if provided."""
    if v is None:
      return []
    return v


class SunsetHourlyAirQualityData(BaseModel):
  """Hourly air quality data from Open-Meteo Air Quality API for sunset analysis."""

  time: list[str] = Field(..., description="Hourly timestamps in ISO format")
  pm10: list[float] = Field(..., description="PM10 particulate matter (μg/m³)")
  pm2_5: list[float] = Field(..., description="PM2.5 particulate matter (μg/m³)")
  us_aqi: list[int] = Field(default_factory=lambda: [], description="US Air Quality Index")
  dust: list[float] = Field(default_factory=lambda: [], description="Dust concentration (μg/m³)")

  @field_validator("us_aqi", "dust", mode="before")
  @classmethod
  def ensure_optional_lists(cls, v, info):
    """Handle optional air quality fields."""
    if v is None:
      return []
    return v


class SunsetWeatherAPIResponse(BaseModel):
  """Complete weather API response from Open-Meteo for sunset analysis."""

  latitude: float = Field(..., description="Location latitude")
  longitude: float = Field(..., description="Location longitude")
  timezone: str = Field(..., description="Timezone identifier")
  timezone_abbreviation: str = Field(..., description="Timezone abbreviation")
  daily: SunsetDailyWeatherData = Field(..., description="Daily weather data")
  hourly: SunsetHourlyWeatherData = Field(..., description="Hourly weather data")


class SunsetAirQualityAPIResponse(BaseModel):
  """Air quality API response from Open-Meteo for sunset analysis."""

  latitude: float = Field(..., description="Location latitude")
  longitude: float = Field(..., description="Location longitude")
  timezone: str = Field(..., description="Timezone identifier")
  timezone_abbreviation: str = Field(..., description="Timezone abbreviation")
  hourly: SunsetHourlyAirQualityData = Field(..., description="Hourly air quality data")


class SunsetCombinedWeatherData(BaseModel):
  """Combined weather and air quality data for sunset analysis."""

  weather: SunsetWeatherAPIResponse = Field(..., description="Weather data")
  air_quality: SunsetAirQualityAPIResponse = Field(..., description="Air quality data")


class SunsetHourConditions(BaseModel):
  """Weather conditions for a specific hour in sunset analysis."""

  visibility: float = Field(..., description="Visibility in meters")
  cloud_low: float = Field(..., description="Low cloud coverage %")
  cloud_mid: float = Field(..., description="Mid cloud coverage %")
  cloud_high: float = Field(..., description="High cloud coverage %")
  precipitation: float = Field(..., description="Total precipitation in mm")
  pressure: float = Field(..., description="Surface pressure in hPa")
  temperature: float = Field(..., description="Temperature in Celsius")
  pm10: float = Field(..., description="PM10 particulate matter (μg/m³)")
  pm2_5: float = Field(..., description="PM2.5 particulate matter (μg/m³)")
  aqi: int = Field(..., description="US Air Quality Index")

  @property
  def total_cloud_coverage(self) -> float:
    """Calculate total cloud coverage."""
    return self.cloud_low + self.cloud_mid + self.cloud_high

  @property
  def visibility_km(self) -> float:
    """Get visibility in kilometers."""
    return self.visibility / 1000

  @property
  def has_air_quality_data(self) -> bool:
    """Check if air quality data is available."""
    return self.pm10 is not None and self.pm2_5 is not None


class SunsetCloudScoreBreakdown(BaseModel):
  """Detailed breakdown of cloud scoring components for sunset analysis."""

  mid_score: float = Field(..., description="Score from mid-level clouds")
  overcast_penalty: float = Field(..., description="Penalty for overcast conditions")
  low_penalty: float = Field(..., description="Penalty for low clouds")
  high_bonus: float = Field(..., description="Bonus for high clouds")
  total: float = Field(..., description="Total cloud score")


class SunsetHourlyScores(BaseModel):
  """Scoring breakdown for one hour in sunset analysis."""

  visibility_score: float = Field(..., description="Visibility component score")
  cloud_score: float = Field(..., description="Total cloud score")
  cloud_breakdown: SunsetCloudScoreBreakdown = Field(..., description="Detailed cloud scoring")
  air_quality_score: float = Field(..., description="Air quality/particulate matter score")
  precipitation_penalty: float = Field(..., description="Precipitation penalty")
  pressure_bonus: float = Field(..., description="High pressure bonus")
  total_score: float = Field(..., description="Total sunset quality score")


class SunsetHourlyAnalysis(BaseModel):
  """Analysis results for one hour in the sunset window."""

  time: str = Field(..., description="Time in HH:MM format")
  iso_time: str = Field(..., description="Full ISO timestamp")
  sun_elevation: float = Field(..., description="Sun elevation angle in degrees")
  elevation_weight: float = Field(..., description="Scoring weight based on sun elevation")
  total_score: float = Field(..., description="Total sunset score")
  raw_score: float = Field(..., description="Score before elevation weighting")
  visibility_score: float = Field(..., description="Visibility component")
  cloud_score: float = Field(..., description="Cloud component")
  air_quality_score: float = Field(..., description="Air quality component")
  precipitation_penalty: float = Field(..., description="Precipitation penalty")
  pressure_bonus: float = Field(..., description="Pressure bonus")
  notes: str = Field(..., description="Descriptive notes for this hour")
  raw_conditions: SunsetHourConditions = Field(..., description="Raw weather conditions")


class SunsetLocationInfo(BaseModel):
  """Geographic location information for sunset analysis."""

  latitude: float = Field(..., description="Location latitude")
  longitude: float = Field(..., description="Location longitude")
  timezone: str = Field(..., description="Timezone identifier")


class SunsetConditionsSummary(BaseModel):
  """Summary of weather conditions at peak sunset time."""

  sun_elevation: float = Field(..., description="Sun elevation angle at peak time")
  visibility_km: float = Field(..., description="Visibility in kilometers")
  cloud_low: float = Field(..., description="Low cloud coverage %")
  cloud_mid: float = Field(..., description="Mid cloud coverage %")
  cloud_high: float = Field(..., description="High cloud coverage %")
  total_cloud_coverage: float = Field(..., description="Total cloud coverage %")
  precipitation_mm: float = Field(..., description="Precipitation in mm")
  pressure_hpa: float = Field(..., description="Surface pressure in hPa")
  temperature_c: float = Field(..., description="Temperature in Celsius")
  pm10: float = Field(..., description="PM10 particulate matter (μg/m³)")
  pm2_5: float = Field(..., description="PM2.5 particulate matter (μg/m³)")
  aqi: int = Field(..., description="US Air Quality Index")


class SunsetAnalysisResult(BaseModel):
  """Complete sunset analysis results for LLM agent consumption."""

  peak_score: float = Field(..., description="Highest sunset quality score in analysis window")
  peak_time: str = Field(..., description="Time of peak conditions (HH:MM)")
  peak_sun_elevation: float = Field(..., description="Sun elevation angle at peak time")
  rating: str = Field(..., description="Qualitative rating (Exceptional, Very Good, etc.)")
  sunset_time: str = Field(..., description="Actual sunset time (HH:MM)")
  golden_hour_start: str = Field(..., description="Golden hour start time (HH:MM)")
  golden_hour_end: str = Field(..., description="Golden hour end time (HH:MM)")
  hourly_analysis: list[SunsetHourlyAnalysis] = Field(..., description="Hour-by-hour analysis")
  conditions_summary: SunsetConditionsSummary = Field(
    ..., description="Weather summary at peak time"
  )
  location: SunsetLocationInfo = Field(..., description="Geographic location")
  flags: list[str] = Field(..., description="Special condition flags")


# Golden Hour Calculation Functions


def calculate_sun_position(
  dt: datetime, latitude: float, longitude: float, timezone: str
) -> Tuple[float, float]:
  """
  Calculate sun elevation and azimuth angles for a given time and location.

  Args:
      dt: Datetime (timezone-aware)
      latitude: Location latitude
      longitude: Location longitude
      timezone: Timezone string

  Returns:
      Tuple of (elevation_angle, azimuth_angle) in degrees
  """
  # Create pandas DatetimeIndex for pvlib
  times = pd.DatetimeIndex([dt], tz=timezone)

  # Calculate solar position
  solar_position = pvlib.solarposition.get_solarposition(
    times, latitude, longitude, method="nrel_numpy"
  )

  elevation = solar_position["elevation"].iloc[0]
  azimuth = solar_position["azimuth"].iloc[0]

  return elevation, azimuth


def find_golden_hour_window(
  sunset_date: date,
  latitude: float,
  longitude: float,
  timezone: str,
  upper_elevation: float = 6.0,
  lower_elevation: float = -4.0,
) -> Tuple[datetime, datetime]:
  """
  Find the golden hour window based on sun elevation angles.

  Golden hour occurs when sun elevation is between 6° and -4°.
  Blue hour occurs when sun elevation is between -4° and -6°.

  Args:
      sunset_date: Date to analyze
      latitude: Location latitude
      longitude: Location longitude
      timezone: Timezone string
      upper_elevation: Upper bound of golden hour (default 6°)
      lower_elevation: Lower bound of golden hour (default -4°)

  Returns:
      Tuple of (start_time, end_time) for golden hour window
  """
  # Start search 3 hours before midnight to ensure we catch evening golden hour
  search_start = datetime.combine(sunset_date, datetime.min.time()).replace(
    hour=15, tzinfo=pd.Timestamp.now(tz=timezone).tzinfo
  )
  search_end = search_start.replace(hour=23, minute=59)

  # Generate minute-by-minute timestamps
  time_range = pd.date_range(search_start, search_end, freq="1min")

  # Calculate sun positions for all timestamps
  solar_position = pvlib.solarposition.get_solarposition(
    time_range, latitude, longitude, method="nrel_numpy"
  )

  elevations = solar_position["elevation"].values

  # Find when sun crosses upper and lower elevation thresholds
  golden_hour_start = None
  golden_hour_end = None

  for i in range(len(elevations)):
    if golden_hour_start is None and elevations[i] <= upper_elevation:
      golden_hour_start = time_range[i].to_pydatetime()

    if golden_hour_start is not None and elevations[i] <= lower_elevation:
      golden_hour_end = time_range[i].to_pydatetime()
      break

  # Handle edge cases
  if golden_hour_start is None:
    # Sun never drops below upper elevation (polar summer)
    golden_hour_start = search_start

  if golden_hour_end is None:
    # Sun never drops below lower elevation
    golden_hour_end = search_end

  return golden_hour_start, golden_hour_end


def calculate_elevation_weight(elevation: float) -> float:
  """
  Calculate scoring weight based on sun elevation angle.

  Optimal viewing is when sun is between 0° and 3° elevation.
  Weight decreases as we move away from this range.

  Args:
      elevation: Sun elevation angle in degrees

  Returns:
      Weight multiplier (0.5 to 1.0)
  """
  if 0 <= elevation <= 3:
    # Optimal range - full weight
    return 1.0
  elif -2 <= elevation < 0:
    # Very good - slight reduction
    return 0.95
  elif 3 < elevation <= 6:
    # Good but getting high - gradual reduction
    return 1.0 - (elevation - 3) * 0.1  # 0.7 to 1.0
  elif -4 <= elevation < -2:
    # Getting dark but still good - gradual reduction
    return 0.9 + (elevation + 2) * 0.1  # 0.7 to 0.9
  else:
    # Outside golden hour range
    return 0.5


# Core Analysis Functions


def calculate_air_quality_score(conditions: SunsetHourConditions) -> float:
  """
  Calculate air quality score for sunset viewing (0-20 points).

  Particulate matter has complex effects on sunsets:
  - Small amounts enhance color scattering (dramatic reds/oranges)
  - Too much reduces visibility and washes out colors
  - Sweet spot around 10-25 μg/m³ PM2.5 for optimal color enhancement
  """
  if not conditions.has_air_quality_data:
    return 10  # Neutral score when no data available

  pm2_5 = conditions.pm2_5
  pm10 = conditions.pm10

  # PM2.5 is more important for light scattering effects
  # Optimal range: 10-25 μg/m³ for color enhancement
  # Below 5: too clean, minimal color enhancement
  # Above 35: too hazy, reduced visibility

  if pm2_5 <= 5:
    # Very clean air - good visibility but minimal color enhancement
    pm2_5_score = 12
  elif 5 < pm2_5 <= 15:
    # Ideal range for color enhancement
    pm2_5_score = 18 + (pm2_5 - 5) * 0.2  # Peak at 20 points around 15 μg/m³
  elif 15 < pm2_5 <= 25:
    # Still good for colors, slight visibility reduction
    pm2_5_score = 20 - (pm2_5 - 15) * 0.3
  elif 25 < pm2_5 <= 35:
    # Moderate haze, colors muted but still visible
    pm2_5_score = 17 - (pm2_5 - 25) * 0.5
  elif 35 < pm2_5 <= 55:
    # Heavy haze, significant visibility reduction
    pm2_5_score = 12 - (pm2_5 - 35) * 0.3
  else:
    # Unhealthy air, poor sunset viewing
    pm2_5_score = max(0, 6 - (pm2_5 - 55) * 0.1)

  # PM10 penalty for dust/large particles that reduce clarity
  pm10_penalty = 0
  if pm10 > 50:
    pm10_penalty = -(pm10 - 50) * 0.1

  total_score = pm2_5_score + pm10_penalty
  return max(0, min(20, total_score))


def analyze_sunset_conditions(
  target_date: date,
  weather: SunsetWeatherAPIResponse,
  air_quality: SunsetAirQualityAPIResponse,
) -> SunsetAnalysisResult:
  """
  Analyze sunset conditions and return structured scoring results.

  Args:
      weather_data: Weather API data from Open-Meteo
      air_quality_data: Optional air quality API data from Open-Meteo
      target_date: Date to analyze (YYYY-MM-DD), defaults to first date in data

  Returns:
      Structured analysis results for the LLM agent
  """

  try:
    date_index = weather.daily.time.index(target_date.isoformat())
    sunset_time_str = weather.daily.sunset[date_index]
  except (ValueError, IndexError):
    raise ValueError(f"Date {target_date} not found in weather data")

  # Parse sunset time
  sunset_time = datetime.fromisoformat(sunset_time_str.replace("Z", "+00:00"))

  # Calculate golden hour window based on sun elevation
  start_time, end_time = find_golden_hour_window(
    target_date, weather.latitude, weather.longitude, weather.timezone
  )

  # Extract hourly data
  hourly_times = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in weather.hourly.time]

  # Find relevant hourly indices
  analysis_indices = []
  analysis_times = []

  for i, dt in enumerate(hourly_times):
    if start_time <= dt <= end_time:
      analysis_indices.append(i)
      analysis_times.append(dt)

  if not analysis_indices:
    raise ValueError("No hourly data found in sunset analysis window")

  # Calculate scores for each hour
  hourly_analysis = []
  peak_score = 0
  peak_time = None
  peak_conditions = None
  peak_elevation = None

  for i, time_idx in enumerate(analysis_indices):
    hour_conditions = extract_hour_conditions(weather.hourly, air_quality.hourly, time_idx)
    scores = calculate_hourly_score(hour_conditions)

    # Calculate sun elevation for this hour
    sun_elevation, _ = calculate_sun_position(
      analysis_times[i], weather.latitude, weather.longitude, weather.timezone
    )

    # Apply elevation-based weighting
    elevation_weight = calculate_elevation_weight(sun_elevation)
    weighted_score = scores.total_score * elevation_weight

    analysis_hour = SunsetHourlyAnalysis(
      time=analysis_times[i].strftime("%H:%M"),
      iso_time=analysis_times[i].isoformat(),
      sun_elevation=round(sun_elevation, 2),
      elevation_weight=round(elevation_weight, 2),
      total_score=round(weighted_score, 1),
      raw_score=round(scores.total_score, 1),
      visibility_score=scores.visibility_score,
      cloud_score=scores.cloud_score,
      air_quality_score=scores.air_quality_score,
      precipitation_penalty=scores.precipitation_penalty,
      pressure_bonus=scores.pressure_bonus,
      notes=generate_hour_notes(hour_conditions, scores),
      raw_conditions=hour_conditions,
    )

    hourly_analysis.append(analysis_hour)

    if weighted_score > peak_score:
      peak_score = weighted_score
      peak_time = analysis_times[i].strftime("%H:%M")
      peak_conditions = hour_conditions
      peak_elevation = sun_elevation

  # Determine rating
  rating = get_rating_from_score(peak_score)

  if peak_conditions is None:
    raise ValueError("No valid peak conditions found in analysis window")
  if peak_time is None:
    raise ValueError("No valid peak time found in analysis window")

  # Generate summary conditions
  conditions_summary = SunsetConditionsSummary(
    sun_elevation=round(peak_elevation, 2) if peak_elevation is not None else 0.0,
    visibility_km=round(peak_conditions.visibility_km, 1),
    cloud_low=peak_conditions.cloud_low,
    cloud_mid=peak_conditions.cloud_mid,
    cloud_high=peak_conditions.cloud_high,
    total_cloud_coverage=peak_conditions.total_cloud_coverage,
    precipitation_mm=peak_conditions.precipitation,
    pressure_hpa=peak_conditions.pressure,
    temperature_c=peak_conditions.temperature,
    pm10=peak_conditions.pm10,
    pm2_5=peak_conditions.pm2_5,
    aqi=peak_conditions.aqi,
  )

  # Generate analysis flags
  flags = generate_analysis_flags(hourly_analysis, peak_conditions)

  # Create location info
  location = SunsetLocationInfo(
    latitude=weather.latitude, longitude=weather.longitude, timezone=weather.timezone
  )

  return SunsetAnalysisResult(
    peak_score=round(peak_score, 1),
    peak_time=peak_time,
    peak_sun_elevation=round(peak_elevation, 2) if peak_elevation is not None else 0.0,
    rating=rating,
    sunset_time=sunset_time.strftime("%H:%M"),
    golden_hour_start=start_time.strftime("%H:%M"),
    golden_hour_end=end_time.strftime("%H:%M"),
    hourly_analysis=hourly_analysis,
    conditions_summary=conditions_summary,
    location=location,
    flags=flags,
  )


def extract_hour_conditions(
  hourly_data: SunsetHourlyWeatherData,
  air_quality_data: SunsetHourlyAirQualityData,
  time_idx: int,
) -> SunsetHourConditions:
  """Extract relevant weather and air quality conditions for a specific hour."""

  # Handle missing rain/showers data gracefully
  rain = hourly_data.rain[time_idx] if time_idx < len(hourly_data.rain) else 0.0
  showers = hourly_data.showers[time_idx] if time_idx < len(hourly_data.showers) else 0.0

  # Extract air quality data
  pm10 = air_quality_data.pm10[time_idx]
  pm2_5 = air_quality_data.pm2_5[time_idx]
  aqi = air_quality_data.us_aqi[time_idx]

  return SunsetHourConditions(
    visibility=hourly_data.visibility[time_idx],
    cloud_low=hourly_data.cloud_cover_low[time_idx],
    cloud_mid=hourly_data.cloud_cover_mid[time_idx],
    cloud_high=hourly_data.cloud_cover_high[time_idx],
    precipitation=rain + showers,
    pressure=hourly_data.surface_pressure[time_idx],
    temperature=hourly_data.temperature_2m[time_idx],
    pm10=pm10,
    pm2_5=pm2_5,
    aqi=aqi,
  )


def calculate_visibility_score(visibility_meters: float) -> float:
  """Calculate visibility score (0-30 points)."""
  visibility_km = visibility_meters / 1000

  if visibility_km >= 50:
    return 30
  elif visibility_km >= 20:
    return 30
  else:
    return min(30, visibility_km * 1.5)


def calculate_cloud_score(conditions: SunsetHourConditions) -> SunsetCloudScoreBreakdown:
  """Calculate cloud scoring with all components."""
  total_coverage = conditions.total_cloud_coverage

  # Mid-level clouds (primary factor) - 0-40 points
  if 20 <= conditions.cloud_mid <= 60:
    mid_score = 40 - abs(conditions.cloud_mid - 40) * 0.5
  elif conditions.cloud_mid < 20:
    mid_score = conditions.cloud_mid * 1.5
  else:  # cloud_mid > 60
    mid_score = max(0, 40 - (conditions.cloud_mid - 60) * 0.8)

  # Overcast penalty
  overcast_penalty = 0
  if total_coverage >= 180:  # Multi-layer overcast
    overcast_penalty = -40
    mid_score = 0  # Override positive scoring
  elif total_coverage >= 100:  # Single layer overcast
    overcast_penalty = -30
    mid_score = 0  # Override positive scoring

  # Low cloud penalty
  low_penalty = 0
  if conditions.cloud_low > 50:
    low_penalty = -(conditions.cloud_low - 50) * 0.3

  # High cloud bonus (only when not overcast)
  high_bonus = 0
  if total_coverage < 100:
    high_bonus = min(15, conditions.cloud_high * 0.2)

  total_cloud_score = mid_score + overcast_penalty + low_penalty + high_bonus

  return SunsetCloudScoreBreakdown(
    mid_score=mid_score,
    overcast_penalty=overcast_penalty,
    low_penalty=low_penalty,
    high_bonus=high_bonus,
    total=total_cloud_score,
  )


def calculate_hourly_score(conditions: SunsetHourConditions) -> SunsetHourlyScores:
  """Calculate total score for one hour including air quality."""

  # Visibility score (0-30 points)
  visibility_score = calculate_visibility_score(conditions.visibility)

  # Cloud score (complex calculation)
  cloud_breakdown = calculate_cloud_score(conditions)
  cloud_score = cloud_breakdown.total

  # Air quality score (0-20 points)
  air_quality_score = calculate_air_quality_score(conditions)

  # Precipitation penalty
  precipitation_penalty = conditions.precipitation * -10

  # Pressure stability bonus
  pressure_bonus = 5 if conditions.pressure > 1020 else 0

  # Total score (now out of 75 base points instead of 55)
  total_score = (
    visibility_score + cloud_score + air_quality_score + precipitation_penalty + pressure_bonus
  )

  return SunsetHourlyScores(
    visibility_score=visibility_score,
    cloud_score=cloud_score,
    cloud_breakdown=cloud_breakdown,
    air_quality_score=air_quality_score,
    precipitation_penalty=precipitation_penalty,
    pressure_bonus=pressure_bonus,
    total_score=max(0, total_score),  # Don't go below 0
  )


def generate_hour_notes(conditions: SunsetHourConditions, scores: SunsetHourlyScores) -> str:
  """Generate descriptive notes for an hour."""
  notes = []

  # Visibility notes
  if conditions.visibility_km < 15:
    notes.append("Poor visibility")
  elif conditions.visibility_km > 30:
    notes.append("Excellent visibility")

  # Cloud notes
  if conditions.total_cloud_coverage >= 100:
    notes.append("Overcast conditions")
  elif conditions.cloud_low > 60:
    notes.append("Low clouds may obstruct horizon")
  elif 20 <= conditions.cloud_mid <= 60:
    notes.append("Ideal mid-level clouds for color")

  # Air quality notes
  if conditions.has_air_quality_data:
    if conditions.pm2_5 <= 5:
      notes.append("Very clean air")
    elif 10 <= conditions.pm2_5 <= 25:
      notes.append("Optimal particulates for color enhancement")
    elif conditions.pm2_5 > 35:
      notes.append("Hazy conditions from air pollution")

  # Precipitation notes
  if conditions.precipitation > 0.1:
    notes.append("Light precipitation")

  # Pressure notes
  if conditions.pressure > 1020:
    notes.append("Stable high pressure")

  return "; ".join(notes) if notes else "Clear conditions"


def get_rating_from_score(score: float) -> str:
  """Convert numerical score to rating category."""
  if score >= 80:
    return "Exceptional"
  elif score >= 65:
    return "Very Good"
  elif score >= 50:
    return "Good"
  elif score >= 35:
    return "Fair"
  elif score >= 20:
    return "Poor"
  else:
    return "Awful"


def generate_analysis_flags(
  hourly_analysis: list[SunsetHourlyAnalysis], peak_conditions: SunsetHourConditions
) -> list[str]:
  """Generate analysis flags for special conditions."""
  flags = []

  # Check sun elevation at peak time
  if hourly_analysis:
    peak_analysis = max(hourly_analysis, key=lambda x: x.total_score)
    if 0 <= peak_analysis.sun_elevation <= 3:
      flags.append("optimal_sun_elevation")
    elif peak_analysis.sun_elevation > 6:
      flags.append("sun_too_high")
    elif peak_analysis.sun_elevation < -4:
      flags.append("past_golden_hour")

  # Check for overcast penalty
  if peak_conditions.total_cloud_coverage >= 100:
    flags.append("overcast_penalty_applied")

  # Check visibility
  if peak_conditions.visibility_km >= 30:
    flags.append("excellent_visibility")
  elif peak_conditions.visibility_km < 15:
    flags.append("poor_visibility")

  # Check for ideal cloud conditions
  if 20 <= peak_conditions.cloud_mid <= 60 and peak_conditions.total_cloud_coverage < 100:
    flags.append("ideal_mid_clouds")

  # Check for precipitation impact
  if peak_conditions.precipitation > 0.5:
    flags.append("precipitation_impact")

  # Check pressure stability
  if peak_conditions.pressure > 1020:
    flags.append("stable_pressure")

  # Check air quality conditions
  if peak_conditions.has_air_quality_data:
    if peak_conditions.pm2_5 <= 5:
      flags.append("very_clean_air")
    elif 10 <= peak_conditions.pm2_5 <= 25:
      flags.append("optimal_particulates")
    elif peak_conditions.pm2_5 > 35:
      flags.append("hazy_conditions")

    if peak_conditions.aqi and peak_conditions.aqi > 100:
      flags.append("unhealthy_air_quality")

  return flags


# Example usage and test function
def test_sunset_analysis():
  """Test function using sample weather data with air quality."""
  # Sample weather data structure
  sample_weather = {
    "latitude": 43.688763,
    "longitude": -79.29532,
    "timezone": "America/Toronto",
    "timezone_abbreviation": "EDT",
    "daily": {
      "time": ["2025-06-05"],
      "sunrise": ["2025-06-05T05:36"],
      "sunset": ["2025-06-05T20:55"],
      "temperature_2m_min": [15.2],
      "temperature_2m_max": [25.3],
      "wind_speed_10m_max": [20],
    },
    "hourly": {
      "time": ["2025-06-05T18:00", "2025-06-05T19:00", "2025-06-05T20:00", "2025-06-05T21:00"],
      "cloud_cover_low": [82, 32, 100, 55],
      "cloud_cover_mid": [39, 0, 0, 0],
      "cloud_cover_high": [52, 0, 0, 0],
      "visibility": [21400, 20600, 19900, 17600],
      "rain": [0, 0, 0, 0],
      "showers": [0, 0, 0, 0],
      "surface_pressure": [1001.2, 1000.6, 1000.5, 1000.8],
      "temperature_2m": [21.1, 20.7, 20.3, 19.3],
    },
  }

  # Sample air quality data
  sample_air_quality = {
    "latitude": 43.688763,
    "longitude": -79.29532,
    "hourly": {
      "time": ["2025-06-05T18:00", "2025-06-05T19:00", "2025-06-05T20:00", "2025-06-05T21:00"],
      "pm10": [8.5, 7.8, 9.0, 10.2],
      "pm2_5": [5.2, 4.9, 6.1, 7.3],
      "us_aqi": [32, 29, 35, 38],
    },
  }

  try:
    # Test with air quality data
    result = analyze_sunset_conditions(
      date(2025, 6, 5),
      SunsetWeatherAPIResponse.model_validate(sample_weather),
      SunsetAirQualityAPIResponse.model_validate(sample_air_quality),
    )
    print("Sunset Analysis Results (with air quality):")
    print(f"Peak Score: {result.peak_score}")
    print(f"Rating: {result.rating}")
    print(f"Peak Time: {result.peak_time}")
    print(f"Air Quality Score: {result.hourly_analysis[0].air_quality_score}")
    print(f"PM2.5: {result.conditions_summary.pm2_5} μg/m³")
    print(f"Flags: {', '.join(result.flags)}")

    return result
  except Exception as e:
    print(f"Error in analysis: {e}")
    return None


if __name__ == "__main__":
  test_sunset_analysis()
