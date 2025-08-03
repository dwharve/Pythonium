"""
LLM client module for interacting with OpenAI compatible APIs.

This module provides a client for interacting with OpenAI compatible APIs,
which can be used for testing and production code.
"""

import os
from typing import AsyncIterator, Dict, List, Optional, Union

from openai import AsyncOpenAI
from pydantic import BaseModel

from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    """Configuration for the LLM client."""

    api_key: str = "dummy_key_for_local_testing"
    base_url: str = "http://localhost:80/v1"
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    timeout: int = 30


class LLMMessage(BaseModel):
    """Message model for LLM interactions."""

    role: str
    content: str


class LLMError(Exception):
    """Exception raised for LLM-related errors."""

    pass


class LLMClient:
    """Client for interacting with OpenAI compatible APIs."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM client.

        Args:
            config: Configuration for the LLM client. If not provided,
                   will be loaded from environment variables or default values.
        """
        self.config = config or self._load_config_from_env()
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )
        logger.debug(f"Initialized LLM client with base URL: {self.config.base_url}")

    def _load_config_from_env(self) -> LLMConfig:
        """Load LLM configuration from environment variables."""
        return LLMConfig(
            api_key=os.environ.get("OPENAI_API_KEY", "dummy_key_for_local_testing"),
            base_url=os.environ.get("OPENAI_API_BASE", "http://localhost:80/v1"),
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
            top_p=float(os.environ.get("OPENAI_TOP_P", "1.0")),
            max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "0")) or None,
            presence_penalty=float(os.environ.get("OPENAI_PRESENCE_PENALTY", "0.0")),
            frequency_penalty=float(os.environ.get("OPENAI_FREQUENCY_PENALTY", "0.0")),
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Union[str, AsyncIterator[str]]:
        """Get chat completion from the LLM API.

        Args:
            messages: List of messages in the conversation
            stream: Whether to stream the response
            model: Optional override for the model
            temperature: Optional override for temperature
            max_tokens: Optional override for max tokens

        Returns:
            If stream=False, returns the complete response text.
            If stream=True, returns an async iterator of response chunks.

        Raises:
            LLMError: If an error occurs during the API call
        """
        try:
            if stream:
                return self._handle_streaming_completion(
                    messages, model, temperature, max_tokens
                )
            else:
                return await self._handle_non_streaming_completion(
                    messages, model, temperature, max_tokens
                )
        except Exception as e:
            raise LLMError(f"Error during LLM API call: {str(e)}") from e

    async def _handle_non_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Handle non-streaming completion."""
        response = await self.client.chat.completions.create(
            model=model or self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
        )
        return response.choices[0].message.content or ""

    async def _handle_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Handle streaming completion."""
        stream = await self.client.chat.completions.create(
            model=model or self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
            stream=True,
        )

        async for chunk in stream:  # type: ignore[union-attr]
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def prompt_variation(
        self,
        prompt: str,
        instruction: str,
        agent_type: Optional[str] = None,
    ) -> str:
        """Generate a variation of a prompt based on the instruction.

        Args:
            prompt: The original prompt text
            instruction: Instruction on how to modify the prompt
            agent_type: Optional agent type to specialize the prompt for

        Returns:
            The modified prompt

        Raises:
            LLMError: If an error occurs during the API call
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI prompt engineering expert. Your task is to modify prompts "
                    "according to specific instructions while maintaining the core purpose "
                    "of the original prompt."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original prompt: {prompt}\n\n"
                    f"Instruction: {instruction}\n\n"
                    + (
                        f"Optimize for agent type: {agent_type}\n\n"
                        if agent_type
                        else ""
                    )
                    + "Create a modified version of the prompt that follows the instruction. "
                    "Return only the modified prompt text without any additional explanations."
                ),
            },
        ]

        try:
            response = await self._handle_non_streaming_completion(messages)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating prompt variation: {str(e)}")
            raise LLMError(f"Failed to generate prompt variation: {str(e)}")
