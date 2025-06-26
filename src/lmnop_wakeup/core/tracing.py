import functools
import inspect
import os
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

import logfire
import structlog
from langfuse.api import Prompt_Chat

# Global variables for ambient tracing information
_user_id: str | None = None
_session_id: str | None = None

logger = structlog.get_logger()


def initialize_tracing():
  # Configure Logfire for use with Langfuse
  logfire.configure(
    service_name="lmnop:wakeup",
    send_to_logfire=False,
    scrubbing=False,
    code_source=logfire.CodeSource(
      repository="https://github.com/shyndman/lmnop-wakeup/",
      revision="main",
      root_path="/",
    ),
  ).with_settings(
    console_log=False,
  )
  logfire.instrument_mcp()
  logfire.instrument_pydantic_ai(event_mode="logs")
  logfire.instrument_pydantic(record="failure")
  logfire.instrument_httpx(capture_all=True)
  # logfire.instrument_psycopg()
  # logfire.instrument_sqlite3()

  from RandomWordGenerator import RandomWord

  """
  Initializes ambient tracing information (user ID and session ID).
  This function should be called once at the start of the application.
  """
  global _user_id, _session_id

  # Get Linux username
  _user_id = os.getenv("LANGFUSE_USER") or os.getlogin()

  # Generate session ID (3 random kebab-cased words)
  word_list: list[str] | None = RandomWord(max_word_size=8).getList(num_of_words=3)
  if word_list is not None:
    _session_id = "-".join(word_list)
  else:
    # Handle the case where getList returns None, maybe assign a default or log a warning
    _session_id = "unknown-session"  # Assign a default value for now


class LangfuseSpanContext:
  """
  Context manager to create a Logfire span and add Langfuse-specific attributes.
  Sets span name, user ID, session ID, and optional tags.
  """

  def __init__(self, name: str, tags: list[str] | None = None, prompt: Prompt_Chat | None = None):
    self.name = name
    self.tags = tags
    self.prompt = prompt
    self._logfire_span = None  # To store the Logfire span context manager

  def __enter__(self):
    import logfire

    # Create and enter the Logfire span context manager
    span = self._logfire_span = logfire.span(self.name)
    self._logfire_span.__enter__()  # Get the actual span object

    if span and span.is_recording():
      # Set ambient attributes from global variables
      if _user_id is not None:
        span.set_attribute("langfuse.user.id", _user_id)
      if _session_id is not None:
        span.set_attribute("langfuse.session.id", _session_id)
      if self.prompt is not None:
        logger.info(f"Recording prompt: {self.prompt.name}")
        span.set_attribute("langfuse.prompt.name", self.prompt.name)
        span.set_attribute("langfuse.prompt.version", self.prompt.version)

      # Set optional tags
      if self.tags:
        span.set_attribute("langfuse.tags", self.tags)

    return self

  def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    if self._logfire_span:
      self._logfire_span.__exit__(exc_type, exc_val, exc_tb)
      self._logfire_span = None

  def set_attribute(self, key: str, value: Any) -> None:
    """
    Sets an attribute on the current span.

    Args:
      key: The attribute key
      value: The attribute value

    Raises:
      RuntimeError: If called outside a span context
    """
    if not self._logfire_span:
      raise RuntimeError("Cannot set attribute outside of span context")
    self._logfire_span.set_attribute(key, value)


def langfuse_span(
  name: str, tags: list[str] | None = None, prompt: Prompt_Chat | None = None
) -> LangfuseSpanContext:
  """
  Creates a LangfuseSpanContext context manager instance.

  Args:
      name: The name of the span.
      tags: Optional list of tags to add to the span.

  Returns:
      An instance of LangfuseSpanContext.
  """
  return LangfuseSpanContext(name=name, tags=tags, prompt=prompt)


_P = ParamSpec("_P")
_R = TypeVar("_R")
_F = TypeVar("_F", bound=Callable[..., Any])


def trace(name: str | None = None):
  """
  A decorator that wraps an async function with a Langfuse span.
  The span will have the same name as the function, unless name is specified.
  """

  def trace_async_decorator(
    func: Callable[_P, Coroutine[Any, Any, _R]],
  ) -> Callable[_P, Coroutine[Any, Any, _R]]:
    @functools.wraps(func)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
      if not inspect.iscoroutinefunction(func):
        raise TypeError(f"Function {func.__name__} is not an async function.")

      with langfuse_span(name=name or func.__name__):
        return await func(*args, **kwargs)

    return wrapper

  return trace_async_decorator


def trace_sync(name: str | None = None):
  """
  A decorator that wraps a synchronous function with a Langfuse span.
  The span will have the same name as the function, unless name is specified.
  """

  def trace_sync_decorator(
    func: Callable[_P, _R],
  ) -> Callable[_P, _R]:
    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
      try:
        with langfuse_span(name=name or func.__name__):
          logger.info(f"entering {name or func.__name__}")
          return func(*args, **kwargs)
      finally:
        logger.info(f"exiting {name or func.__name__}")

    return wrapper

  return trace_sync_decorator
