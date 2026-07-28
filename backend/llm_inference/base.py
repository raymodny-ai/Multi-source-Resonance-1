"""
LLM client base class — abstract provider interface for OpenAI/Anthropic.

Defines the common interface all LLM providers must implement:
- complete(): send prompt and get response
- stream_complete(): streaming response (optional)
- is_available(): check if API key is configured
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Raised when an LLM provider call fails."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for LLM API clients.

    Subclasses implement provider-specific API calls (OpenAI, Anthropic, etc.)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self._api_key = api_key or self._get_env_key()
        self._model = model or self._default_model()
        self._available = bool(self._api_key)

    @abstractmethod
    def _get_env_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        ...

    @abstractmethod
    def _default_model(self) -> str:
        """Return the default model name for this provider."""
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return self.__class__.__name__

    @property
    def is_available(self) -> bool:
        """Check if this provider has a valid API key."""
        return self._available

    @property
    def model(self) -> str:
        """Current model name."""
        return self._model

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a completion request to the LLM API.

        Args:
            prompt: User prompt text.
            system_prompt: Optional system instruction.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            dict with 'content', 'model', 'usage' keys.

        Raises:
            LLMProviderError: On API call failure.
        """
        ...

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> Any:
        """Streaming completion (optional, not all providers support).

        Default implementation falls back to non-streaming complete().
        """
        return await self.complete(prompt, system_prompt, max_tokens, temperature)


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible client (works with OpenAI, DeepSeek, OpenRouter, etc.).

    Configure via env:
      OPENAI_API_KEY   (required when is_available matters)
      OPENAI_BASE_URL  (default: https://api.openai.com/v1) — set to
                       https://api.deepseek.com/v1 for DeepSeek etc.
      OPENAI_MODEL     (default: gpt-4o)
    """

    def _get_env_key(self) -> Optional[str]:
        return os.environ.get("OPENAI_API_KEY")

    def _default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o")

    def _api_url(self) -> str:
        """Build chat completions URL, honoring OPENAI_BASE_URL override."""
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        return f"{base}/chat/completions"

    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Call OpenAI Chat Completion API."""
        if not self._available:
            raise LLMProviderError("OpenAI API key not configured")

        import httpx

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self._api_url(), json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "content": content,
                "model": self._model,
                "provider": "openai",
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            }
        except Exception as e:
            raise LLMProviderError(f"OpenAI API call failed: {e}") from e


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def _get_env_key(self) -> Optional[str]:
        return os.environ.get("ANTHROPIC_API_KEY")

    def _default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Call Anthropic Messages API."""
        if not self._available:
            raise LLMProviderError("Anthropic API key not configured")

        import httpx

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self.API_URL, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["content"][0]["text"]
            usage = data.get("usage", {})

            return {
                "content": content,
                "model": self._model,
                "provider": "anthropic",
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                },
            }
        except Exception as e:
            raise LLMProviderError(f"Anthropic API call failed: {e}") from e


def get_default_client() -> BaseLLMClient:
    """Get the first available LLM client (OpenAI preferred, then Anthropic).

    Returns:
        An available BaseLLMClient instance.

    Raises:
        LLMProviderError: If no provider is available.
    """
    openai_client = OpenAIClient()
    if openai_client.is_available:
        return openai_client

    anthropic_client = AnthropicClient()
    if anthropic_client.is_available:
        return anthropic_client

    raise LLMProviderError("No LLM provider configured (need OPENAI_API_KEY or ANTHROPIC_API_KEY)")
