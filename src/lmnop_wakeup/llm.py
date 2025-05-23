import functools
import re
from dataclasses import dataclass
from typing import cast

from langfuse import Langfuse
from langfuse.api import ChatMessage
from langfuse.api.core import RequestOptions
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from .common import get_litellm_api_key

GEMINI_25_FLASH = "gemini/gemini-2.5-flash-preview-05-20"
GEMINI_25_PRO = "gemini/gemini-2.5-pro-preview-03-25"


LATEST_PROMPT_LABEL = "latest"
PRODUCTION_PROMPT_LABEL = "production"


def create_litellm_model(gemini_model_name: str) -> OpenAIModel:
  litellm_key = get_litellm_api_key()
  provider = OpenAIProvider(
    openai_client=AsyncOpenAI(
      api_key=litellm_key,
      base_url="http://litellm.don/",
    ),
  )
  return OpenAIModel(gemini_model_name, provider=provider)


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
