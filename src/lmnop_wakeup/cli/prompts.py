"""CLI commands for working with Langfuse prompts."""

from typing import cast, override

import structlog
from clypi import Command
from langfuse import Langfuse
from langfuse.api import Prompt_Chat
from langfuse.api.core import RequestOptions
from rich.console import Console

from ..llm import PRODUCTION_PROMPT_LABEL

logger = structlog.get_logger()
console = Console()


class DumpPrompts(Command):
  """Dump all agent prompts from Langfuse to the terminal with markdown formatting"""

  @override
  async def run(self):
    """Fetch and display all agent prompts from Langfuse."""

    # List of prompt names to fetch
    prompt_names = [
      "event_prioritizer",
      "script_writer",
      "content_optimizer",
      "scheduler",
      "sunset_oracle",
      "meteorologist",
    ]

    langfuse = Langfuse()

    all_prompts_content = []

    for prompt_name in prompt_names:
      try:
        # Fetch prompt from Langfuse using the same pattern as llm.py
        response = langfuse.api.prompts.get(
          prompt_name,
          label=PRODUCTION_PROMPT_LABEL,
          request_options=RequestOptions(
            max_retries=5,
            timeout_in_seconds=20,
          ),
        )

        raw_prompt = cast(Prompt_Chat, response)

        # Get the raw prompt messages without variable substitution
        messages = raw_prompt.prompt

        # Combine system and user messages into a single content string
        content_parts = []
        for message in messages:
          role = message.role
          content = message.content
          if content and content.strip():
            content_parts.append(f"**{role.capitalize()}:**\n{content}")

        combined_content = "\n\n".join(content_parts)

        # Format with H1 header and content
        prompt_section = f"# {prompt_name}\n\n{combined_content}"
        all_prompts_content.append(prompt_section)

        logger.info(f"Successfully fetched prompt: {prompt_name}")

      except Exception as e:
        error_section = f"# {prompt_name}\n\n**Error:** Failed to fetch prompt - {str(e)}"
        all_prompts_content.append(error_section)
        logger.error(f"Failed to fetch prompt {prompt_name}: {e}")

    # Join all prompts with horizontal rules
    final_output = "\n\n---\n\n".join(all_prompts_content)

    # Print to terminal
    console.print(final_output)
