import os
from importlib.metadata import version

import nest_asyncio
from platformdirs import AppDirs

from .core.logging import initialize_logging
from .core.tracing import initialize_tracing

# Permit the user of nested asyncio.run calls
nest_asyncio.apply()

initialize_tracing()
initialize_logging(log_level=os.getenv("LOG_LEVEL", "DEBUG").upper())

PACKAGE = __name__.split(".")[0]
__version__ = version(PACKAGE)

APP_DIRS = AppDirs(
  appname=PACKAGE,
  appauthor=False,
  version=__version__,
  ensure_exists=True,
)
