import nest_asyncio

from lmnop_wakeup.logging import initialize_logging

# Permit the user of nested asyncio.run calls
nest_asyncio.apply()

initialize_logging()
