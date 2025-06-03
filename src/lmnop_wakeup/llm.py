import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from google import genai
from google.genai.types import HttpOptions
from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.callbacks import AsyncCallbackManager
from langchain_core.outputs import Generation, LLMResult
from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse
from langfuse.api import Prompt_Chat
from langfuse.api.core import RequestOptions
from langfuse.model import ChatPromptClient
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServer
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.settings import ModelSettings

from .core.tracing import langfuse_span
from .env import ApiKey, EnvName, get_litellm_api_key


class ModelName(StrEnum):
  GEMINI_25_FLASH = "gemini-2.5-flash-preview-05-20"
  GEMINI_25_PRO = "gemini-2.5-pro-preview-03-25"
  GEMINI_20_FLASH = "gemini-2.0-flash"
  GEMINI_20_FLASH_LITE = "gemini-2.0-flash-lite"


LATEST_PROMPT_LABEL = "latest"
PRODUCTION_PROMPT_LABEL = "production"


class LiteLlmGooglePassthroughProvider(GoogleProvider):
  def __init__(
    self,
    api_url: str | None = None,
    litellm_virtual_key: ApiKey | None = None,
  ):
    api_url = api_url or os.environ[EnvName.LITELLM_API_URL]
    if not api_url:
      raise ValueError("litellm_api_url is a required argument")

    api_key = litellm_virtual_key or os.environ[EnvName.LITELLM_API_KEY]
    if not api_key:
      raise ValueError("litellm_virtual_key is a required argument")

    super().__init__(
      client=genai.Client(
        api_key=api_key,
        http_options=HttpOptions(base_url=api_url),
      )
    )


def create_litellm_model(name: ModelName) -> Model:
  litellm_key = get_litellm_api_key()
  provider = LiteLlmGooglePassthroughProvider(
    litellm_virtual_key=litellm_key,
  )
  return GoogleModel(name, provider=provider)


@dataclass
class LangfusePromptBundle:
  name: str
  instructions: str
  task_prompt_templates: str
  model_settings: ModelSettings


class LangfuseAgentInput(ABC, BaseModel):
  """Protocol for Langfuse input data.

  This protocol defines the expected structure of input data for Langfuse agents.
  It is used to ensure that the input data passed to the agent matches the expected format.
  """

  @property
  def prompt_variables_supplied(self) -> set[str]:
    return {k for k in self.to_prompt_variable_map().keys()}

  @abstractmethod
  def to_prompt_variable_map(self) -> dict[str, str]:
    raise NotImplementedError("to_prompt_variable_map must be implemented in subclasses")


@dataclass
class AgentContext[Input: LangfuseAgentInput]:
  """Context object passed to LangfuseAgent's underlying pydantic-ai Agent.

  Contains the system and user prompts for the agent, as supplied by langfuse.
  """

  def __init__(self, input: Input, instructions_prompt: str, user_prompt: str):
    self.input = input
    self.instructions_prompt = instructions_prompt
    self.user_prompt = user_prompt


class PydanticAiCallback(AsyncCallbackHandler):
  """Custom callback handler for Pydantic-AI LLM calls"""

  async def before_run(self, model_name: str, prompt: str, **kwargs) -> uuid.UUID:
    """Call this when starting a Pydantic-AI LLM call"""
    run_id = uuid.uuid4()

    # Simulate LangChain's on_llm_start callback
    await self.on_llm_start(
      serialized={"name": model_name, "provider": "pydantic-ai"},
      prompts=[prompt],
      run_id=run_id,
      **kwargs,
    )
    return run_id

  async def after_run(self, run_id: uuid.UUID, response: str, **kwargs):
    """Call this when Pydantic-AI LLM call completes"""
    # Simulate LangChain's on_llm_end callback
    llm_result = LLMResult(
      generations=[
        [Generation(text=response)],
      ]
    )
    await self.on_llm_end(llm_result, run_id=run_id, **kwargs)

  async def error_encountered(self, run_id: uuid.UUID, error: Exception, **kwargs):
    """Call this when Pydantic-AI LLM call fails"""
    await self.on_llm_error(error, run_id=run_id, **kwargs)


def extract_pydantic_ai_callback(config: RunnableConfig) -> PydanticAiCallback:
  cb_mgr = cast(AsyncCallbackManager, config.get("callbacks", []))

  for cb in cb_mgr.handlers:
    if isinstance(cb, PydanticAiCallback):
      return cb

  """Extract the Pydantic-AI callback from the config."""
  raise EnvironmentError(
    "Pydantic-AI callback not found in RunnableConfig. "
    "Ensure you are using a PydanticAiCallback instance in your config."
  )


class LmnopAgent[Input: LangfuseAgentInput, Output: BaseModel]:
  """A pydantic-ai Agent wrapper that integrates with Langfuse prompts and tracing.

  This class provides a standardized way to create agents that:
  - Fetch prompts from Langfuse and render them with runtime inputs
  - Automatically wrap runs in tracing spans with input/output attributes
  - Expose the underlying agent's decorator methods for tool registration

  The agent renders Langfuse prompts at runtime using the @instructions pattern,
  allowing for prompt reuse across different inputs while maintaining type safety.
  """

  def __init__(
    self,
    agent: Agent[AgentContext[Input], Output],
    prompt_name: str,
    raw_prompt: Prompt_Chat,
    model_name: ModelName,
    callback: PydanticAiCallback | None = None,
  ):
    """Initialize with a configured pydantic-ai Agent and Langfuse prompt.

    Args:
      agent: The underlying pydantic-ai Agent instance
      prompt_name: Name of the Langfuse prompt for tracing
      raw_prompt: Raw Langfuse prompt for runtime rendering
    """
    self._agent = agent
    self.prompt_name = prompt_name
    self._raw_prompt = raw_prompt
    self._model_name = model_name
    self._callback = callback

  @classmethod
  def create(
    cls,
    prompt_name: str,
    model_name: ModelName,
    input_type: type[Input],
    output_type: type[Output],
    callback: PydanticAiCallback | None = None,
    mcp_servers: list[MCPServer] = [],
  ) -> "LmnopAgent[Input, Output]":
    """Create a new LangfuseAgent by fetching a prompt from Langfuse.

    Args:
      prompt_name: Name of the prompt in Langfuse
      model: Model name to use (e.g., GEMINI_25_FLASH)
      input_type: TypedDict type for agent inputs
      output_type: Pydantic BaseModel type for agent outputs

    Returns:
      Configured LangfuseAgent instance ready for use
    """
    # Fetch raw prompt from Langfuse
    res = Langfuse().api.prompts.get(
      prompt_name,
      label=PRODUCTION_PROMPT_LABEL,
      request_options=RequestOptions(
        max_retries=5,
        timeout_in_seconds=20,
      ),
    )

    raw_prompt = cast(Prompt_Chat, res)
    model_settings: dict[str, Any] = res.config
    if (
      model_name != ModelName.GEMINI_25_FLASH
      and model_name != ModelName.GEMINI_25_PRO
      and "google_thinking_config" in model_settings
    ):
      del model_settings["google_thinking_config"]

    # Create agent without instructions (will be set via decorator)
    agent = Agent(
      model=create_litellm_model(model_name),
      deps_type=AgentContext[Input],
      output_type=output_type,
      model_settings={"timeout": 60, **ModelSettings(res.config)},
      retries=5,
      instrument=True,
      mcp_servers=mcp_servers,
    )

    # Set up the instructions decorator function
    @agent.instructions
    def rendered_instructions(ctx: RunContext[AgentContext[Input]]) -> str:
      return ctx.deps.instructions_prompt

    return cls(agent, prompt_name, raw_prompt, model_name, callback)

  async def run(self, input: Input) -> Output:
    """Run the agent with the given inputs, wrapped in a tracing span.

    Args:
      inputs: Input data matching the Input TypedDict type

    Returns:
      Agent output matching the Output BaseModel type
    """
    with langfuse_span(name=f"run {self.prompt_name}") as span:
      async with self._agent.run_mcp_servers():
        # Set input attribute on span
        span.set_attribute("input.value", input)

        # Create context and run agent
        system_prompt, user_prompt = self._prepare_prompts(input)
        if self._callback is not None:
          run_id = await self._callback.before_run(str(self._model_name), system_prompt)
        else:
          run_id = None

        ctx = AgentContext(input=input, instructions_prompt=system_prompt, user_prompt=user_prompt)
        result = await self._run_internal(ctx, run_id)
        if self._callback is not None and run_id is not None:
          await self._callback.after_run(run_id, str(result.all_messages_json(), encoding="utf-8"))

        # Set output attribute on span
        span.set_attribute("output.value", result.output)

        return result.output

  async def _run_internal(self, ctx: AgentContext, run_id: uuid.UUID | None = None):
    try:
      return await self._agent.run(user_prompt=ctx.user_prompt, deps=ctx)
    except Exception as error:
      # If an error occurs, call the callback's error handler
      if self._callback is not None and run_id is not None:
        await self._callback.error_encountered(run_id=run_id, error=error)
      raise

  def output_validator(self, *args, **kwargs):
    """Decorator to register an output validator function.
    Optionally takes RunContext as its first argument. Can decorate a sync or async functions."""
    return self._agent.output_validator(*args, **kwargs)

  # Expose agent decorators for tool registration
  def tool_plain(self, *args, **kwargs):
    """Expose the underlying agent's tool_plain decorator."""
    return self._agent.tool_plain(*args, **kwargs)

  def tool(self, *args, **kwargs):
    """Expose the underlying agent's tool decorator."""
    return self._agent.tool(*args, **kwargs)

  def _prepare_prompts(self, input: Input) -> tuple[str, str]:
    """Prepare the system and user prompts from the version downloaded from Langfuse."""
    client = ChatPromptClient(self._raw_prompt)
    missing_vars = set(client.variables).difference(input.prompt_variables_supplied)
    if len(missing_vars) > 1:
      raise ValueError(
        f"Prompt {self._raw_prompt.name} input variables do not satisfy, missing={missing_vars}"
      )

    prompt_messages = client.compile(
      **input.to_prompt_variable_map(),
    )
    if not (
      len(prompt_messages) == 2
      and prompt_messages[0]["role"] == "system"
      and prompt_messages[1]["role"] == "user"
    ):
      raise ValueError(
        "Prompt must contain exactly two messages: system instructions and user prompt"
      )

    system, user = prompt_messages
    return system["content"], user["content"]
