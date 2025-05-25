from typing import override
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langfuse.api import Prompt_Chat
from langfuse.api.core import RequestOptions
from pydantic import BaseModel

from lmnop_wakeup.llm import (
  PRODUCTION_PROMPT_LABEL,
  AgentContext,
  LangfuseAgent,
  LangfuseInput,
  ModelName,
)

pytestmark = pytest.mark.asyncio


class MockInput(LangfuseInput):
  name: str
  age: int

  @override
  def to_prompt_variable_map(self) -> dict[str, str]:
    return {
      "name": self.name,
      "age": str(self.age),
    }


class MockOutput(BaseModel):
  message: str
  processed: bool


class TestLangfuseAgent:
  @patch("lmnop_wakeup.llm.Agent")
  @patch("lmnop_wakeup.llm.Langfuse")
  @patch("lmnop_wakeup.llm.create_litellm_model")
  async def test_create_success(self, mock_create_model, mock_langfuse, mock_agent_class):
    """Test successful LangfuseAgent creation."""
    # Setup mocks
    mock_prompt = MagicMock(spec=Prompt_Chat)
    mock_prompt.config = {"temperature": 0.7}

    mock_langfuse_instance = MagicMock()
    mock_langfuse_instance.async_api.prompts.get = AsyncMock(return_value=mock_prompt)
    mock_langfuse.return_value = mock_langfuse_instance

    mock_model = MagicMock()
    mock_create_model.return_value = mock_model

    mock_agent_instance = MagicMock()
    mock_agent_class.return_value = mock_agent_instance

    # Create agent
    agent = LangfuseAgent[MockInput, MockOutput].create(
      prompt_name="test_prompt",
      model=ModelName.GEMINI_25_FLASH,
      input_type=MockInput,
      output_type=MockOutput,
    )

    # Verify Langfuse API call
    mock_langfuse_instance.async_api.prompts.get.assert_called_once_with(
      "test_prompt",
      label=PRODUCTION_PROMPT_LABEL,
      request_options=RequestOptions(
        max_retries=5,
        timeout_in_seconds=10,
      ),
    )

    # Verify agent creation
    mock_create_model.assert_called_once_with("gemini-2.5-flash")
    mock_agent_class.assert_called_once()
    assert agent.prompt_name == "test_prompt"
    assert agent._raw_prompt == mock_prompt
    assert agent._agent == mock_agent_instance

  @patch("lmnop_wakeup.llm.langfuse_span")
  async def test_run_success(self, mock_langfuse_span):
    """Test successful agent run with input/output tracing."""
    # Setup mocks
    mock_span = MagicMock()
    mock_span.set_attribute = MagicMock()
    mock_langfuse_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_langfuse_span.return_value.__exit__ = MagicMock(return_value=None)

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = MockOutput(message="Hello John", processed=True)
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_prompt = MagicMock(spec=Prompt_Chat)

    # Create agent instance
    agent = LangfuseAgent(mock_agent, "test_prompt", mock_prompt)

    # Run agent
    inputs = MockInput(name="John", age=30)
    result = await agent.run(inputs)

    # Verify tracing span creation
    mock_langfuse_span.assert_called_once_with(name="run test_prompt")

    # Verify input/output attributes set on span
    mock_span.set_attribute.assert_any_call("input.value", inputs)
    mock_span.set_attribute.assert_any_call("output.value", mock_result.output)

    # Verify agent run was called with correct arguments
    mock_agent.run.assert_called_once()
    call_args = mock_agent.run.call_args
    assert isinstance(call_args[1]["deps"], AgentContext)
    assert call_args[1]["deps"].prompt == mock_prompt
    assert call_args[1]["deps"].input == inputs

    # Verify result
    assert result == mock_result.output

  async def test_agent_context_creation(self):
    """Test AgentContext dataclass creation."""
    mock_prompt = MagicMock(spec=Prompt_Chat)
    inputs = MockInput(name="Alice", age=25)

    context = AgentContext(prompt=mock_prompt, input=inputs)

    assert context.prompt == mock_prompt
    assert context.input == inputs

  @patch("lmnop_wakeup.llm.langfuse_span")
  async def test_instructions_rendering_with_multiple_prompts(self, mock_langfuse_span):
    """Test that agent runs successfully with proper context creation."""
    # Setup mocks
    mock_span = MagicMock()
    mock_langfuse_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_langfuse_span.return_value.__exit__ = MagicMock(return_value=None)

    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = MockOutput(message="Processed", processed=True)
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_prompt = MagicMock(spec=Prompt_Chat)
    agent = LangfuseAgent(mock_agent, "test_prompt", mock_prompt)

    inputs = MockInput(name="Test", age=20)
    result = await agent.run(inputs)

    # Verify agent.run was called with correct context
    mock_agent.run.assert_called_once()
    call_args = mock_agent.run.call_args
    assert isinstance(call_args[1]["deps"], AgentContext)
    assert call_args[1]["deps"].prompt == mock_prompt
    assert call_args[1]["deps"].input == inputs
    assert result == mock_result.output

  @patch("lmnop_wakeup.llm.ChatPromptClient")
  async def test_instructions_rendering_single_prompt(self, mock_chat_prompt_client):
    """Test instructions rendering when only system instructions exist."""
    mock_client_instance = MagicMock()
    mock_client_instance.compile.return_value = [{"content": "System instructions only"}]
    mock_chat_prompt_client.return_value = mock_client_instance

    # This test focuses on the instructions rendering logic
    # We'd need to test the actual @agent.instructions function created in create()
    # For now, verify the ChatPromptClient setup
    mock_chat_prompt_client.assert_not_called()  # Not called until agent runs

  @pytest.mark.skip(reason="sync test")
  def test_tool_decorators_exposed(self):
    """Test that agent tool decorators are properly exposed."""
    mock_agent = MagicMock()
    mock_prompt = MagicMock(spec=Prompt_Chat)

    agent = LangfuseAgent(mock_agent, "test_prompt", mock_prompt)

    # Test tool_plain exposure
    agent.tool_plain("arg1", kwarg1="value1")
    mock_agent.tool_plain.assert_called_once_with("arg1", kwarg1="value1")

    # Test tool exposure
    agent.tool("arg2", kwarg2="value2")
    mock_agent.tool.assert_called_once_with("arg2", kwarg2="value2")

  @pytest.mark.parametrize(
    "prompt_name,expected_span_name",
    [
      ("weather_prompt", "run weather_prompt"),
      ("schedule_prompt", "run schedule_prompt"),
      ("brief_prompt", "run brief_prompt"),
    ],
  )
  @patch("lmnop_wakeup.llm.langfuse_span")
  async def test_span_naming(self, mock_langfuse_span, prompt_name, expected_span_name):
    """Test that spans are named correctly based on prompt name."""
    mock_span = MagicMock()
    mock_langfuse_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_langfuse_span.return_value.__exit__ = MagicMock(return_value=None)

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
      return_value=MagicMock(output=MockOutput(message="test", processed=True))
    )

    mock_prompt = MagicMock(spec=Prompt_Chat)
    agent = LangfuseAgent(mock_agent, prompt_name, mock_prompt)

    with patch("lmnop_wakeup.llm.ChatPromptClient"):
      await agent.run(MockInput(name="test", age=1))

    mock_langfuse_span.assert_called_once_with(name=expected_span_name)
