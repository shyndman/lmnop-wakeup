#!/usr/bin/env python3
"""
Example usage of BriefingDirectory and BriefingDirectoryCollection types.

This demonstrates how to work with briefing directories using the new type-safe interface.
"""

import asyncio
from datetime import date, timedelta

from lmnop_wakeup.paths import BriefingDirectory, BriefingDirectoryCollection


async def main():
  print("🗂️  BriefingDirectory Usage Examples\n")

  # Example 1: Working with a specific date
  print("1. Working with a specific briefing directory:")
  today = date.today()
  briefing_dir = BriefingDirectory.for_date(today)

  print(f"   Date: {briefing_dir.briefing_date}")
  print(f"   Path: {briefing_dir.base_path}")
  print(f"   Exists: {briefing_dir.exists()}")
  print(f"   Complete: {briefing_dir.is_complete()}")
  print()

  # Example 2: File paths
  print("2. Expected file paths:")
  print(f"   Brief JSON: {briefing_dir.brief_json_path}")
  print(f"   Workflow State: {briefing_dir.workflow_state_path}")
  print(f"   Master Audio: {briefing_dir.master_audio_path}")
  print()

  # Example 3: Collection operations
  print("3. Working with briefing directory collection:")
  collection = BriefingDirectoryCollection()

  # Discover all existing briefings
  all_briefings = collection.discover_all()
  print(f"   Found {len(all_briefings)} existing briefings")

  # Get latest briefings
  latest = collection.get_latest(3)
  if latest:
    print("   Latest 3 briefings:")
    for i, bd in enumerate(latest, 1):
      status = "✅ complete" if bd.is_complete() else "🔄 partial"
      print(f"     {i}. {bd.briefing_date} - {status}")
  else:
    print("   No existing briefings found")
  print()

  # Example 4: Iteration
  print("4. Iterating over all briefings (descending date order):")
  for i, briefing_dir in enumerate(collection):
    if i >= 5:  # Limit to first 5
      print("     ... (and more)")
      break
    status = "✅" if briefing_dir.is_complete() else "🔄"
    print(f"   {status} {briefing_dir.briefing_date}")
  print()

  # Example 5: Checking for specific dates
  print("5. Checking for specific dates:")
  tomorrow = today + timedelta(days=1)
  yesterday = today - timedelta(days=1)

  for check_date in [yesterday, today, tomorrow]:
    existing = collection.get_existing_for_date(check_date)
    if existing:
      print(f"   {check_date}: Found existing briefing")
    else:
      print(f"   {check_date}: No briefing exists")
  print()

  # Example 6: WAV files (if any exist)
  if briefing_dir.exists():
    wav_files = briefing_dir.wav_files
    if wav_files:
      print("6. WAV files in order:")
      for wav_file in wav_files:
        print(f"   - {wav_file.name}")
    else:
      print("6. No WAV files found in this briefing")
  else:
    print("6. Cannot check WAV files - briefing directory doesn't exist")
  print()

  # Example 7: Loading content (if available)
  if briefing_dir.has_workflow_state():
    try:
      workflow_state = briefing_dir.load_workflow_state()
      print("7. Workflow state loaded successfully:")
      print(f"   Keys: {list(workflow_state.keys())}")
    except Exception as e:
      print(f"7. Failed to load workflow state: {e}")
  else:
    print("7. No workflow state file available")

  if briefing_dir.has_brief_json():
    try:
      briefing_script = briefing_dir.load_script()
      print(f"   Brief script loaded: {len(briefing_script.sections)} sections")
    except Exception as e:
      print(f"   Failed to load brief script: {e}")
  else:
    print("   No brief script file available")


if __name__ == "__main__":
  asyncio.run(main())
