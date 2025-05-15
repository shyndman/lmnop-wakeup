from typing import cast

import logfire
import nest_asyncio
from langfuse import Langfuse
from langfuse.api import ChatMessage
from langfuse.api.core import RequestOptions
from pydantic import BaseModel
from pydantic_ai.settings import ModelSettings

# Permit the user of nested asyncio.run calls
nest_asyncio.apply()

# Configure Logfire for use with Langfuse
logfire.configure(
  service_name="lmnop:wakeup",
  send_to_logfire=False,
  scrubbing=False,
).with_settings(
  console_log=False,
)
logfire.instrument_pydantic_ai(event_mode="logs")
logfire.instrument_pydantic(record="all")
logfire.instrument_httpx()


GEMINI_25_FLASH = "gemini-2.5-flash-preview-04-17"
GEMINI_25_PRO = "gemini-2.5-pro-preview-03-25"


LATEST_PROMPT_LABEL = "latest"
PRODUCTION_PROMPT_LABEL = "production"


class LangfusePromptBundle(BaseModel):
  instructions: str
  model_settings: ModelSettings


async def get_langfuse_prompt_bundle(prompt_name: str) -> LangfusePromptBundle:
  res = await Langfuse().async_api.prompts.get(
    prompt_name,
    label=PRODUCTION_PROMPT_LABEL,
    request_options=RequestOptions(
      max_retries=5,
      timeout_in_seconds=10,
    ),
  )

  instructions, *prompts = res.prompt
  assert len(prompts) == 0

  model_settings = res.config
  return LangfusePromptBundle(
    instructions=cast(ChatMessage, instructions).content,
    model_settings=ModelSettings(model_settings),
  )
