import logging
import sys
from io import StringIO

import logfire
import rich
import structlog
from langchain_core.globals import set_debug, set_verbose
from structlog.types import Processor
from structlog.typing import EventDict

logger = structlog.get_logger()


def rich_sprint(*args, **kwargs) -> str:
  """
  rich.print() to a string, and returns it
  """
  sb = StringIO()
  rich.print(*args, **kwargs, file=sb)
  return sb.getvalue()


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
  """
  Uvicorn logs the message a second time in the extra `color_message`, but we don't
  need it. This processor drops the key from the event dict if it exists.
  """
  event_dict.pop("color_message", None)
  return event_dict


def initialize_logging(json_logs: bool = False, log_level: str = "DEBUG"):
  timestamper = structlog.processors.TimeStamper(utc=False, fmt="%H:%M:%S")

  shared_processors: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.stdlib.ExtraAdder(),
    drop_color_message_key,
    timestamper,
    structlog.processors.StackInfoRenderer(),
  ]

  if json_logs:
    # Format the exception only for JSON logs, as we want to pretty-print them when
    # using the ConsoleRenderer
    shared_processors.append(structlog.processors.format_exc_info)

  structlog.configure(
    processors=shared_processors
    + [
      # Prepare event dict for `ProcessorFormatter`.
      structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
  )

  log_renderer: structlog.types.Processor
  if json_logs:
    log_renderer = structlog.processors.JSONRenderer()
  else:
    log_renderer = structlog.dev.ConsoleRenderer(
      pad_level=False,
      exception_formatter=structlog.dev.RichTracebackFormatter(max_frames=20),
    )

  formatter = structlog.stdlib.ProcessorFormatter(
    # These run ONLY on `logging` entries that do NOT originate within
    # structlog.
    foreign_pre_chain=shared_processors,
    # These run on ALL entries after the pre_chain is done.
    processors=[
      # Remove _record & _from_structlog.
      structlog.stdlib.ProcessorFormatter.remove_processors_meta,
      logfire.StructlogProcessor(),
      log_renderer,
    ],
  )

  handler = logging.StreamHandler()
  # Use OUR `ProcessorFormatter` to format all `logging` entries.
  handler.setFormatter(formatter)
  root_logger = logging.getLogger()
  root_logger.addHandler(handler)
  root_logger.setLevel(log_level.upper())

  # Disable verbose logging
  set_verbose(log_level.upper() == "TRACE")

  # Disable debug logging
  set_debug(log_level.upper() in {"TRACE", "DEBUG"})

  for _log in ["uvicorn", "uvicorn.error"]:
    # Clear the log handlers for uvicorn loggers, and enable propagation
    # so the messages are caught by our root logger and formatted correctly
    # by structlog
    logging.getLogger(_log).handlers.clear()
    logging.getLogger(_log).propagate = True

  # Since we re-create the access logs ourselves, to add all information
  # in the structured log (see the `logging_middleware` in main.py), we clear
  # the handlers and prevent the logs to propagate to a logger higher up in the
  # hierarchy (effectively rendering them silent).
  for _log in ["urllib3", "uvicorn.access", "httpcore"]:
    logging.getLogger(_log).handlers.clear()
    logging.getLogger(_log).propagate = False

  def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Log any uncaught exception instead of letting it be printed by Python
    (but leave KeyboardInterrupt untouched to allow users to Ctrl+C to stop)
    See https://stackoverflow.com/a/16993115/3641865
    """
    if issubclass(exc_type, KeyboardInterrupt):
      sys.__excepthook__(exc_type, exc_value, exc_traceback)
      return

    root_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

  sys.excepthook = handle_exception


# <green>{time:HH:mm:ss}</green> <dim>[{module}]</dim> <level>{level} {message}</level>",
