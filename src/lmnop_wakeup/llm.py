import functools
import os
import re
from dataclasses import dataclass
from typing import cast

from google import genai
from google.genai.types import HttpOptions
from langfuse import Langfuse
from langfuse.api import ChatMessage
from langfuse.api.core import RequestOptions
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.settings import ModelSettings

from .common import ApiKey, EnvName, get_litellm_api_key

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
  res = await Langfuse().async_api.prompts.get(
    prompt_name,
    label=PRODUCTION_PROMPT_LABEL,
    request_options=RequestOptions(
      max_retries=5,
      timeout_in_seconds=10,
    ),
  )

  instructions, *prompts = map(
    lambda p: p.content,
    cast(list[ChatMessage], res.prompt),
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
