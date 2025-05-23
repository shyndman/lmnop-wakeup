import os

# Global variables for ambient tracing information
_user_id: str | None = None
_session_id: str | None = None


def initialize_tracing():
  from RandomWordGenerator import RandomWord

  """
  Initializes ambient tracing information (user ID and session ID).
  This function should be called once at the start of the application.
  """
  global _user_id, _session_id

  # Get Linux username
  _user_id = os.getlogin()

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

  def __init__(self, name: str, tags: list[str] | None = None):
    self.name = name
    self.tags = tags
    self._logfire_span_context = None  # To store the Logfire span context manager

  def __enter__(self):
    import logfire

    # Create and enter the Logfire span context manager
    self._logfire_span_context = logfire.span(self.name)
    span = self._logfire_span_context.__enter__()  # Get the actual span object

    if span and span.is_recording():
      # Set ambient attributes from global variables
      if _user_id is not None:
        span.set_attribute("langfuse.user.id", _user_id)
      if _session_id is not None:
        span.set_attribute("langfuse.session.id", _session_id)

      # Set optional tags
      if self.tags:
        span.set_attribute("langfuse.tags", self.tags)

    return self

  def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    if self._logfire_span_context:
      self._logfire_span_context.__exit__(exc_type, exc_val, exc_tb)


def langfuse_span(name: str, tags: list[str] | None = None) -> LangfuseSpanContext:
  """
  Creates a LangfuseSpanContext context manager instance.

  Args:
      name: The name of the span.
      tags: Optional list of tags to add to the span.

  Returns:
      An instance of LangfuseSpanContext.
  """
  return LangfuseSpanContext(name=name, tags=tags)
