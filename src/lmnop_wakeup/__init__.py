from importlib.metadata import version

import nest_asyncio
from cachetools import LRUCache, TTLCache
from platformdirs import AppDirs
from shelved_cache import PersistentCache

from lmnop_wakeup.core.logging import initialize_logging
from lmnop_wakeup.core.tracing import initialize_tracing

# Permit the user of nested asyncio.run calls
nest_asyncio.apply()

initialize_logging()
initialize_tracing()

PACKAGE = __name__.split(".")[0]
__version__ = version(PACKAGE)

APP_DIRS = AppDirs(
  appname=PACKAGE,
  appauthor=False,
  version=__version__,
  ensure_exists=True,
)

LARGE_FCACHE = PersistentCache(
  LRUCache, filename=str(APP_DIRS.user_cache_path / "large_function_cache.db"), maxsize=2000
)
TTL_FCACHE = PersistentCache(
  TTLCache, filename=str(APP_DIRS.user_cache_path / "large_ttl_cache.db"), maxsize=10, ttl=7200
)
