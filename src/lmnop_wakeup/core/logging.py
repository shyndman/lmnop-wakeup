import inspect
import logging
import logging.config
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
    backtrace=True,
    diagnose=True,
  )
  # HACK(https://github.com/Delgan/loguru/issues/1252): Someone thinks that it makes sense to
  # optimize for aesthetics over THE ABILITY TO READ EXCEPTIONS.
  logger._core.handlers[1]._exception_formatter._max_length = 200  # type: ignore
  logger.opt(exception=True)

  # Intercept log messages from the standard Python logging system
  logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
  logging.config.dictConfig(LOGGING_CONFIG)

  # Intercept Logfire
  logger.configure(handlers=[logfire.loguru_handler()])


class InterceptHandler(logging.Handler):
  @override
  def emit(self, record: logging.LogRecord) -> None:
    # Get corresponding Loguru level if it exists.
    try:
      level: str | int = logger.level(record.levelname).name
    except ValueError:
      level = record.levelno

    record.created //= 1
    record.msecs = 0

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


LOGGING_CONFIG = {
  "version": 1,
  "handlers": {
    "default": {"class": "logging.StreamHandler", "formatter": "http", "stream": "ext://sys.stderr"}
  },
  "formatters": {
    "http": {
      "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
      "datefmt": "%H:%M:%S",
    }
  },
  "loggers": {
    "httpx": {
      "handlers": ["default"],
      "level": "WARNING",
    },
    "httpcore": {
      "handlers": ["default"],
      "level": "WARNING",
    },
    "langgraph": {
      "handlers": ["default"],
      "level": "WARNING",
    },
    "langchain": {
      "handlers": ["default"],
      "level": "WARNING",
    },
    "fastapi": {
      "handlers": ["default"],
      "level": "INFO",
    },
    "uvicorn": {
      "handlers": ["default"],
      "level": "INFO",
    },
    "google.maps": {"handlers": ["default"], "level": "INFO"},
  },
}
