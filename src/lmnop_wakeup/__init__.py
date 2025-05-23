import nest_asyncio

from lmnop_wakeup.tracing import initialize_tracing
from lmnop_wakeup.utils.logging import initialize_logging

# Permit the user of nested asyncio.run calls
nest_asyncio.apply()

initialize_logging()
initialize_tracing()
