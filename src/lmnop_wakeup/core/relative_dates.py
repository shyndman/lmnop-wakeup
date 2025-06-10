"""Utility for formatting relative dates between an anchor and focus date."""

from datetime import date, datetime


def format_relative_date(anchor: date, focus: date | datetime) -> list[str]:
  """Return a list of possible relative date descriptions for focus relative to anchor.

  Args:
      anchor: The reference date (e.g., "today")
      focus: The target date/datetime to describe relative to anchor

  Returns:
      List of string descriptions in order of preference/naturalness

  Examples:
      format_relative_date(date(2024, 1, 15), date(2024, 1, 16))
      # Returns: ["Tomorrow", "Tuesday", "January 16"]

      format_relative_date(date(2024, 1, 15), datetime(2024, 1, 22, 14, 30))
      # Returns: ["Next Monday at 2:30pm", "Next Monday", "A week from Monday at 2:30pm",
      # "January 22 at 2:30pm"]
  """
  descriptions = []

  # Extract date part for calculations
  focus_date = focus.date() if isinstance(focus, datetime) else focus

  # Calculate the difference
  delta = focus_date - anchor
  days_diff = delta.days

  # Format time if focus is a datetime
  def format_time(dt: datetime) -> str:
    hour = dt.hour
    minute = dt.minute

    # Special cases for common times
    if hour == 0 and minute == 0:
      return "midnight"
    elif hour == 12 and minute == 0:
      return "noon"
    elif minute == 0:
      # On the hour
      if hour < 12:
        return f"{hour}am"
      else:
        return f"{hour - 12}pm"
    else:
      # With minutes
      if hour == 0:
        return f"12:{minute:02d}am"
      elif hour < 12:
        return f"{hour}:{minute:02d}am"
      elif hour == 12:
        return f"12:{minute:02d}pm"
      else:
        return f"{hour - 12}:{minute:02d}pm"

  time_suffix = ""
  if isinstance(focus, datetime):
    time_suffix = f" at {format_time(focus)}"

  # Helper variables
  focus_weekday_name = focus_date.strftime("%A")
  focus_month_day = focus_date.strftime("%B %d")

  # Same day
  if days_diff == 0:
    if time_suffix:
      descriptions.append(f"Today{time_suffix}")
    descriptions.append("Today")
    descriptions.append(focus_weekday_name)
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions

  # Yesterday/Tomorrow (±1 day)
  if days_diff == -1:
    if time_suffix:
      descriptions.append(f"Yesterday{time_suffix}")
    descriptions.append("Yesterday")
    descriptions.append(focus_weekday_name)
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions
  elif days_diff == 1:
    if time_suffix:
      descriptions.append(f"Tomorrow{time_suffix}")
    descriptions.append("Tomorrow")
    descriptions.append(focus_weekday_name)
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions

  # This week (within ±6 days)
  if -6 <= days_diff <= 6:
    if days_diff > 0:
      if time_suffix:
        descriptions.append(f"{days_diff} days from now{time_suffix}")
        descriptions.append(f"This {focus_weekday_name}{time_suffix}")
      descriptions.append(f"{days_diff} days from now")
      descriptions.append(f"This {focus_weekday_name}")
    else:
      abs_days = abs(days_diff)
      if time_suffix:
        descriptions.append(f"{abs_days} days ago{time_suffix}")
        descriptions.append(f"Last {focus_weekday_name}{time_suffix}")
      descriptions.append(f"{abs_days} days ago")
      descriptions.append(f"Last {focus_weekday_name}")
    descriptions.append(focus_weekday_name)
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions

  # Next/Last week (±7 to ±13 days)
  if 7 <= days_diff <= 13:
    if time_suffix:
      descriptions.append(f"{days_diff} days from now{time_suffix}")
      descriptions.append(f"Next {focus_weekday_name}{time_suffix}")
    descriptions.append(f"{days_diff} days from now")
    descriptions.append(f"Next {focus_weekday_name}")
    if time_suffix:
      descriptions.append(f"A week from {focus_weekday_name}{time_suffix}")
    descriptions.append(f"A week from {focus_weekday_name}")
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions
  elif -13 <= days_diff <= -7:
    abs_days = abs(days_diff)
    if time_suffix:
      descriptions.append(f"{abs_days} days ago{time_suffix}")
      descriptions.append(f"Last {focus_weekday_name}{time_suffix}")
    descriptions.append(f"{abs_days} days ago")
    descriptions.append(f"Last {focus_weekday_name}")
    if time_suffix:
      descriptions.append(f"A week ago {focus_weekday_name}{time_suffix}")
    descriptions.append(f"A week ago {focus_weekday_name}")
    descriptions.append(focus_month_day)
    if time_suffix:
      descriptions.append(f"{focus_month_day}{time_suffix}")
    return descriptions

  # Multiple weeks away
  if days_diff > 0:
    weeks = days_diff // 7
    if weeks == 2:
      descriptions.append("2 weeks from now")
      if time_suffix:
        descriptions.append(f"2 {focus_weekday_name}s from now{time_suffix}")
      descriptions.append(f"2 {focus_weekday_name}s from now")
    elif weeks <= 4:
      descriptions.append(f"{weeks} weeks from now")
      if time_suffix:
        descriptions.append(f"{weeks} {focus_weekday_name}s from now{time_suffix}")
      descriptions.append(f"{weeks} {focus_weekday_name}s from now")
    else:
      # More than a month, use month descriptions
      if focus_date.month == anchor.month + 1 or (anchor.month == 12 and focus_date.month == 1):
        descriptions.append("Next month")
      descriptions.append(focus_month_day)
      if time_suffix:
        descriptions.append(f"{focus_month_day}{time_suffix}")
      return descriptions
  else:
    weeks = abs(days_diff) // 7
    if weeks == 2:
      descriptions.append("2 weeks ago")
      if time_suffix:
        descriptions.append(f"2 {focus_weekday_name}s ago{time_suffix}")
      descriptions.append(f"2 {focus_weekday_name}s ago")
    elif weeks <= 4:
      descriptions.append(f"{weeks} weeks ago")
      if time_suffix:
        descriptions.append(f"{weeks} {focus_weekday_name}s ago{time_suffix}")
      descriptions.append(f"{weeks} {focus_weekday_name}s ago")
    else:
      # More than a month ago
      if focus_date.month == anchor.month - 1 or (anchor.month == 1 and focus_date.month == 12):
        descriptions.append("Last month")
      descriptions.append(focus_month_day)
      if time_suffix:
        descriptions.append(f"{focus_month_day}{time_suffix}")
      return descriptions

  # Always include the specific day and date as fallbacks
  descriptions.append(focus_weekday_name)
  descriptions.append(focus_month_day)
  if time_suffix:
    descriptions.append(f"{focus_month_day}{time_suffix}")

  return descriptions


def get_best_relative_description(anchor: date, focus: date | datetime) -> str:
  """Get the most natural single description for focus relative to anchor."""
  descriptions = format_relative_date(anchor, focus)
  focus_date = focus.date() if isinstance(focus, datetime) else focus
  return descriptions[0] if descriptions else focus_date.strftime("%B %d")


def get_relative_description_with_fallback(
  anchor: date, focus: date | datetime, max_length: int = 20
) -> str:
  """Get the best relative description that fits within max_length, with fallback."""
  descriptions = format_relative_date(anchor, focus)

  for desc in descriptions:
    if len(desc) <= max_length:
      return desc

  # If nothing fits, return the shortest format possible
  focus_date = focus.date() if isinstance(focus, datetime) else focus
  return focus_date.strftime("%m/%d")
