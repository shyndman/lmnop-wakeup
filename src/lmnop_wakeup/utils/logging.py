import inspect
import logging
import sys
from io import StringIO
from typing import override

import logfire
import rich
from loguru import logger


def rich_sprint(*args, **kwargs) -> str:
  """
  rich.print() to a string, and returns it
  """
  sb = StringIO()
  rich.print(*args, **kwargs, file=sb)
  return sb.getvalue()


def initialize_logging():
  logger.remove()
  logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> <dim>[{module}]</dim> <level>{level} {message}</level>",
  )

  # Configure Logfire for use with Langfuse
  logfire.configure(
    service_name="lmnop:wakeup",
    send_to_logfire=False,
    scrubbing=False,
  ).with_settings(
    console_log=True,
  )
  logfire.instrument_httpx()
  logfire.instrument_pydantic(record="failure")
  logfire.instrument_pydantic_ai(event_mode="logs")
  logfire.instrument_mcp()


class InterceptHandler(logging.Handler):
  @override
  def emit(self, record: logging.LogRecord) -> None:
    # Get corresponding Loguru level if it exists.
    try:
      level: str | int = logger.level(record.levelname).name
    except ValueError:
      level = record.levelno

    # Find caller from where originated the logged message.
    frame, depth = inspect.currentframe(), 0
    while frame:
      filename = frame.f_code.co_filename
      is_logging = filename == logging.__file__
      is_frozen = "importlib" in filename and "_bootstrap" in filename
      if depth > 0 and not (is_logging or is_frozen):
        break
      frame = frame.f_back
      depth += 1

    logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


LOGGING_CONFIG = {
  "version": 1,
  "handlers": {
    "default": {"class": "logging.StreamHandler", "formatter": "http", "stream": "ext://sys.stderr"}
  },
  "formatters": {
    "http": {
      "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S",
    }
  },
  "loggers": {
    "httpx": {
      "handlers": ["default"],
      "level": "DEBUG",
    },
    "httpcore": {
      "handlers": ["default"],
      "level": "DEBUG",
    },
    "google.maps": {"handlers": ["default"], "level": "DEBUG"},
  },
}
