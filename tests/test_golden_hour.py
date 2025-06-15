#!/usr/bin/env python3
"""Test golden hour calculations."""

from datetime import date

from lmnop_wakeup.weather.sunset_scoring import calculate_sun_position, find_golden_hour_window


def test_golden_hour_calculations():
  """Test golden hour calculations for various locations."""
  # Test locations
  locations = [
    ("Toronto", 43.688763, -79.29532, "America/Toronto"),
    ("Quito, Ecuador (Equator)", -0.1807, -78.4678, "America/Guayaquil"),
    ("Reykjavik, Iceland", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    ("Sydney, Australia", -33.8688, 151.2093, "Australia/Sydney"),
  ]

  test_date = date(2025, 6, 15)  # Summer solstice-ish

  results = []

  for name, lat, lon, tz in locations:
    start, end = find_golden_hour_window(test_date, lat, lon, tz)
    duration_minutes = (end - start).total_seconds() / 60

    # Verify sun elevation at boundaries
    start_elev, _ = calculate_sun_position(start, lat, lon, tz)
    end_elev, _ = calculate_sun_position(end, lat, lon, tz)

    results.append(
      {
        "location": name,
        "duration": duration_minutes,
        "start_elev": start_elev,
        "end_elev": end_elev,
      }
    )

    # Print for debugging
    print(f"\n{name}: {duration_minutes:.0f} min ({start_elev:.2f}° to {end_elev:.2f}°)")

    # Assertions
    assert 30 <= duration_minutes <= 180, f"Duration out of expected range for {name}"

    # Handle high latitude edge cases where sun doesn't go below -4°
    if "Iceland" in name and test_date.month in [5, 6, 7]:
      # In summer at high latitudes, sun may not reach -4°
      assert end_elev >= -4, f"Sun should not go far below horizon in {name} summer"
    else:
      assert -5 <= end_elev <= -3, f"End elevation should be near -4° for {name}"

    assert 5 <= start_elev <= 7, f"Start elevation should be near 6° for {name}"

  # Verify equatorial locations have shorter golden hours
  equator_duration = next(r["duration"] for r in results if "Equator" in r["location"])
  toronto_duration = next(r["duration"] for r in results if "Toronto" in r["location"])
  assert equator_duration < toronto_duration, "Equator should have shorter golden hour"


def test_elevation_weight_function():
  """Test the elevation weight function."""
  from lmnop_wakeup.weather.sunset_scoring import calculate_elevation_weight

  # Test optimal range (0-3 degrees)
  assert calculate_elevation_weight(0) == 1.0
  assert calculate_elevation_weight(1.5) == 1.0
  assert calculate_elevation_weight(3) == 1.0

  # Test near-optimal ranges
  assert 0.9 <= calculate_elevation_weight(-1) <= 1.0
  assert 0.8 <= calculate_elevation_weight(4) <= 0.9

  # Test boundaries
  assert calculate_elevation_weight(6) == 0.7
  assert calculate_elevation_weight(-4) == 0.7

  # Test outside golden hour
  assert calculate_elevation_weight(10) == 0.5
  assert calculate_elevation_weight(-10) == 0.5
