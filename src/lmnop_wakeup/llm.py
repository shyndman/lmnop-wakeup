import re
from dataclasses import dataclass
from typing import cast

from langfuse import Langfuse
from langfuse.api import ChatMessage
from langfuse.api.core import RequestOptions
from pydantic_ai.settings import ModelSettings

GEMINI_25_FLASH = "gemini-2.5-flash-preview-04-17"
GEMINI_25_PRO = "gemini-2.5-pro-preview-03-25"


LATEST_PROMPT_LABEL = "latest"
PRODUCTION_PROMPT_LABEL = "production"


@dataclass
class LangfusePromptBundle:
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
    instructions=instructions,
    model_settings=ModelSettings(model_settings),
    task_prompt_templates=prompts,
  )
