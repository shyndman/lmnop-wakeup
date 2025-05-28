import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from google import genai
from google.genai.types import HttpOptions
from langfuse import Langfuse
from langfuse.api import Prompt_Chat
from langfuse.api.core import RequestOptions
from langfuse.model import ChatPromptClient
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
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


HORIZONTAL_RULE = "\n---------\n"


class LangfuseAgentInput(ABC, BaseModel):
  """Protocol for Langfuse input data.

  This protocol defines the expected structure of input data for Langfuse agents.
  It is used to ensure that the input data passed to the agent matches the expected format.
  """

  @property
  def prompt_variables_supplied(self) -> set[str]:
    return set(self.model_dump().keys())

  @abstractmethod
  def to_prompt_variable_map(self) -> dict[str, str]:
    raise NotImplementedError("to_prompt_variable_map must be implemented in subclasses")


@dataclass
class AgentContext[Input: LangfuseAgentInput]:
  """Context object passed to LangfuseAgent's underlying pydantic-ai Agent.

  Contains the system and user prompts for the agent, as supplied by langfuse.
  """

  prompt: Prompt_Chat
  input: Input
  instructions_prompt: str
  user_prompt: str

  def __init__(self, prompt: Prompt_Chat, input: Input):
    self.prompt = prompt
    self.input = input

    client = ChatPromptClient(self.prompt)
    missing_vars = set(client.variables).difference(self.input.prompt_variables_supplied)
    if len(missing_vars) > 1:
      raise ValueError(
        f"Prompt {self.prompt.name} input variables do not satisfy, missing={missing_vars}"
      )

    prompt_messages = client.compile(
      **self.input.to_prompt_variable_map(),
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
    self.instructions_prompt = system["content"]
    self.user_prompt = user["content"]


class LangfuseAgent[Input: LangfuseAgentInput, Output: BaseModel]:
  """A pydantic-ai Agent wrapper that integrates with Langfuse prompts and tracing.

  This class provides a standardized way to create agents that:
  - Fetch prompts from Langfuse and render them with runtime inputs
  - Automatically wrap runs in tracing spans with input/output attributes
  - Expose the underlying agent's decorator methods for tool registration

  The agent renders Langfuse prompts at runtime using the @instructions pattern,
  allowing for prompt reuse across different inputs while maintaining type safety.
  """

  def __init__(
    self, agent: Agent[AgentContext[Input], Output], prompt_name: str, raw_prompt: Prompt_Chat
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

  @classmethod
  def create(
    cls,
    prompt_name: str,
    model: ModelName,
    input_type: type[Input],
    output_type: type[Output],
  ) -> "LangfuseAgent[Input, Output]":
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
        timeout_in_seconds=10,
      ),
    )

    raw_prompt = cast(Prompt_Chat, res)
    model_settings: dict[str, Any] = res.config
    if model != ModelName.GEMINI_25_FLASH and model != ModelName.GEMINI_25_PRO:
      del model_settings["google_thinking_config"]

    # Create agent without instructions (will be set via decorator)
    agent = Agent(
      model=create_litellm_model(model),
      deps_type=AgentContext[Input],
      output_type=output_type,
      model_settings=ModelSettings(res.config),
      instrument=True,
    )

    # Set up the instructions decorator function
    @agent.instructions
    def rendered_instructions(ctx: RunContext[AgentContext[Input]]) -> str:
      return ctx.deps.instructions_prompt

    return cls(agent, prompt_name, raw_prompt)

  async def run(self, input: Input) -> Output:
    """Run the agent with the given inputs, wrapped in a tracing span.

    Args:
      inputs: Input data matching the Input TypedDict type

    Returns:
      Agent output matching the Output BaseModel type
    """
    with langfuse_span(name=f"run {self.prompt_name}") as span:
      # Set input attribute on span
      span.set_attribute("input.value", input)

      # Create context and run agent
      ctx = AgentContext(prompt=self._raw_prompt, input=input)
      result = await self._agent.run(user_prompt=ctx.user_prompt, deps=ctx)

      # Set output attribute on span
      span.set_attribute("output.value", result.output)

      return result.output

  # Expose agent decorators for tool registration
  def tool_plain(self, *args, **kwargs):
    """Expose the underlying agent's tool_plain decorator."""
    return self._agent.tool_plain(*args, **kwargs)

  def tool(self, *args, **kwargs):
    """Expose the underlying agent's tool decorator."""
    return self._agent.tool(*args, **kwargs)
