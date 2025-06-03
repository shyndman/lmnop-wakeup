import os
from pathlib import Path

from .. import APP_DIRS


def get_data_path() -> Path:
  """Get the data directory path, checking DATA_PATH env var first."""
  data_path_env = os.getenv("DATA_PATH")
  if data_path_env:
    return Path(data_path_env)
  return APP_DIRS.user_state_path
