import functools
import os
import re
from dataclasses import dataclass
from typing import cast

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

from .common import ApiKey, EnvName, get_litellm_api_key
from .tracing import langfuse_span

GEMINI_25_FLASH = "gemini-2.5-flash-preview-05-20"
GEMINI_25_PRO = "gemini-2.5-pro-preview-03-25"


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


def create_litellm_model(gemini_model_name: str) -> Model:
  litellm_key = get_litellm_api_key()
  provider = LiteLlmGooglePassthroughProvider(
    litellm_virtual_key=litellm_key,
  )
  return GoogleModel(gemini_model_name, provider=provider)


@dataclass
class LangfusePromptBundle:
  name: str
  instructions: str
  task_prompt_templates: str
  model_settings: ModelSettings


HORIZONTAL_RULE = "\n---------\n"
langfuse_template_pattern = re.compile(r"{{\s*(\w+)\s*}}", re.NOFLAG)


async def get_langfuse_prompt_bundle(prompt_name: str) -> LangfusePromptBundle:
  input = {}
  res = await Langfuse().async_api.prompts.get(
    prompt_name,
    label=PRODUCTION_PROMPT_LABEL,
    request_options=RequestOptions(
      max_retries=5,
      timeout_in_seconds=10,
    ),
  )
  prompt_chat_messages = ChatPromptClient(cast(Prompt_Chat, res)).compile(**input)
  instructions, *prompts = map(
    lambda p: p["content"],
    prompt_chat_messages,
  )
  prompts = HORIZONTAL_RULE.join(prompts)
  model_settings = res.config

  # Replace double-braced syntax with single, so str.format will format successfully
  prompts = langfuse_template_pattern.sub(r"{\g<1>}", prompts)

  return LangfusePromptBundle(
    name=prompt_name,
    instructions=instructions,
    model_settings=ModelSettings(model_settings),
    task_prompt_templates=prompts,
  )


ApplicationAgent = functools.partial(
  Agent,
  model=GEMINI_25_FLASH,
)


@dataclass
class AgentContext[Input: BaseModel]:
  """Context object passed to LangfuseAgent's underlying pydantic-ai Agent.

  Contains the raw Langfuse prompt and the input data needed for template rendering.
  This allows the agent's @instructions decorator to render prompts with runtime inputs.
  """

  prompt: Prompt_Chat
  input: Input


class LangfuseAgent[Input: BaseModel, Output: BaseModel]:
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
  async def create(
    cls,
    prompt_name: str,
    model: str,
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
    res = await Langfuse().async_api.prompts.get(
      prompt_name,
      label=PRODUCTION_PROMPT_LABEL,
      request_options=RequestOptions(
        max_retries=5,
        timeout_in_seconds=10,
      ),
    )
    raw_prompt = cast(Prompt_Chat, res)

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
      """Render Langfuse prompt with runtime input data."""
      prompt_chat_messages = ChatPromptClient(ctx.deps.prompt).compile(
        **ctx.deps.input.model_dump(),
      )
      instructions, *prompts = map(lambda p: p["content"], prompt_chat_messages)
      if prompts:
        return f"{instructions}\n{HORIZONTAL_RULE}\n{HORIZONTAL_RULE.join(prompts)}"
      return instructions

    return cls(agent, prompt_name, raw_prompt)

  async def run(self, inputs: Input) -> Output:
    """Run the agent with the given inputs, wrapped in a tracing span.

    Args:
      inputs: Input data matching the Input TypedDict type

    Returns:
      Agent output matching the Output BaseModel type
    """
    with langfuse_span(name=f"run {self.prompt_name}") as span:
      # Set input attribute on span
      span.set_attribute("input.value", inputs)

      # Create context and run agent
      ctx = AgentContext(prompt=self._raw_prompt, input=inputs)
      result = await self._agent.run(deps=ctx)

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
