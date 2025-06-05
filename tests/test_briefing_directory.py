import json
import tempfile
from datetime import date
from pathlib import Path

from lmnop_wakeup.paths import BriefingDirectory, BriefingDirectoryCollection


class TestBriefingDirectory:
  def test_for_date_creates_correct_path(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)

      assert briefing_dir.briefing_date == test_date
      assert briefing_dir.base_path == data_path / "2025-01-06"

  def test_file_path_properties(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)

      assert briefing_dir.brief_json_path == briefing_dir.base_path / "brief.json"
      assert briefing_dir.workflow_state_path == briefing_dir.base_path / "workflow_state.json"
      assert briefing_dir.master_audio_path == briefing_dir.base_path / "master_briefing.mp3"

  def test_exists_false_when_directory_missing(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)

      assert not briefing_dir.exists()

  def test_ensure_exists_creates_directory(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)

      briefing_dir.ensure_exists()
      assert briefing_dir.exists()
      assert briefing_dir.base_path.is_dir()

  def test_has_file_methods(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)
      briefing_dir.ensure_exists()

      # Initially no files exist
      assert not briefing_dir.has_brief_json()
      assert not briefing_dir.has_workflow_state()
      assert not briefing_dir.has_master_audio()
      assert not briefing_dir.is_complete()

      # Create files
      briefing_dir.brief_json_path.write_text('{"sections": []}')
      briefing_dir.workflow_state_path.write_text('{"status": "complete"}')
      briefing_dir.master_audio_path.write_text("dummy audio content")

      # Now files exist
      assert briefing_dir.has_brief_json()
      assert briefing_dir.has_workflow_state()
      assert briefing_dir.has_master_audio()
      assert briefing_dir.is_complete()

  def test_load_workflow_state(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)
      briefing_dir.ensure_exists()

      test_state = {"status": "complete", "duration": 120}
      briefing_dir.workflow_state_path.write_text(json.dumps(test_state))

      loaded_state = briefing_dir.load_workflow_state()
      assert loaded_state == test_state

  def test_wav_files_sorted_by_number(self):
    test_date = date(2025, 1, 6)
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      briefing_dir = BriefingDirectory.for_date(test_date, data_path)
      briefing_dir.ensure_exists()

      # Create wav files out of order
      (briefing_dir.base_path / "5.wav").write_text("audio5")
      (briefing_dir.base_path / "1.wav").write_text("audio1")
      (briefing_dir.base_path / "10.wav").write_text("audio10")
      (briefing_dir.base_path / "3.wav").write_text("audio3")

      wav_files = briefing_dir.wav_files
      expected_order = [
        briefing_dir.base_path / "1.wav",
        briefing_dir.base_path / "3.wav",
        briefing_dir.base_path / "5.wav",
        briefing_dir.base_path / "10.wav",
      ]

      assert wav_files == expected_order


class TestBriefingDirectoryCollection:
  def test_discover_all_finds_date_directories(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      collection = BriefingDirectoryCollection(data_path)

      # Create some date directories
      (data_path / "2025-01-06").mkdir()
      (data_path / "2025-01-05").mkdir()
      (data_path / "2025-01-07").mkdir()
      # Create a non-date directory that should be ignored
      (data_path / "not-a-date").mkdir()

      briefing_dirs = collection.discover_all()

      # Should find 3 valid date directories, sorted by date descending
      assert len(briefing_dirs) == 3
      assert briefing_dirs[0].briefing_date == date(2025, 1, 7)
      assert briefing_dirs[1].briefing_date == date(2025, 1, 6)
      assert briefing_dirs[2].briefing_date == date(2025, 1, 5)

  def test_get_latest(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      collection = BriefingDirectoryCollection(data_path)

      # Create date directories
      (data_path / "2025-01-05").mkdir()
      (data_path / "2025-01-06").mkdir()
      (data_path / "2025-01-07").mkdir()

      latest_2 = collection.get_latest(2)

      assert len(latest_2) == 2
      assert latest_2[0].briefing_date == date(2025, 1, 7)
      assert latest_2[1].briefing_date == date(2025, 1, 6)

  def test_get_for_date(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      collection = BriefingDirectoryCollection(data_path)

      test_date = date(2025, 1, 6)
      briefing_dir = collection.get_for_date(test_date)

      assert briefing_dir.briefing_date == test_date
      assert briefing_dir.base_path == data_path / "2025-01-06"

  def test_get_existing_for_date(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      collection = BriefingDirectoryCollection(data_path)

      # Create one directory
      existing_date = date(2025, 1, 6)
      (data_path / "2025-01-06").mkdir()

      # Test existing directory
      existing_dir = collection.get_existing_for_date(existing_date)
      assert existing_dir is not None
      assert existing_dir.briefing_date == existing_date

      # Test non-existing directory
      non_existing_date = date(2025, 1, 7)
      non_existing_dir = collection.get_existing_for_date(non_existing_date)
      assert non_existing_dir is None

  def test_iteration(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      data_path = Path(tmpdir)
      collection = BriefingDirectoryCollection(data_path)

      # Create date directories
      dates = [date(2025, 1, 5), date(2025, 1, 6), date(2025, 1, 7)]
      for d in dates:
        (data_path / d.isoformat()).mkdir()

      # Test iteration (should be in descending order)
      iterated_dates = [bd.briefing_date for bd in collection]
      expected_dates = [date(2025, 1, 7), date(2025, 1, 6), date(2025, 1, 5)]

      assert iterated_dates == expected_dates
