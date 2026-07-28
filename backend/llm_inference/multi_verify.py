"""
Multi-LLM cross-verification — GPT-4o + Claude comparison.

Sends the same prompt to multiple LLM providers and compares responses
for consistency. Detects disagreements and increases confidence when
multiple providers agree.

Usage:
    verifier = MultiLLMVerifier()
    result = await verifier.verify(prompt, context)
"""

import asyncio
import logging
from typing import Any, Optional

from backend.llm_inference.base import (
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    LLMProviderError,
)
from backend.llm_inference.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class VerificationResult:
    """Result from multi-LLM cross-verification."""

    def __init__(
        self,
        responses: list[dict[str, Any]],
        agreement: float,
        consensus_signal: str,
        details: dict[str, Any],
    ):
        self.responses = responses
        self.agreement = agreement  # 0.0-1.0
        self.consensus_signal = consensus_signal  # bullish/bearish/neutral
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "responses": self.responses,
            "agreement": self.agreement,
            "consensus_signal": self.consensus_signal,
            "details": self.details,
        }


class MultiLLMVerifier:
    """Cross-verify LLM outputs across multiple providers.

    Sends the same prompt to all available providers and compares
    their signal assessments. High agreement increases confidence.
    """

    def __init__(self, clients: Optional[list[BaseLLMClient]] = None) -> None:
        """Initialize with optional custom client list.

        Args:
            clients: List of LLM clients to use. If None, auto-detects
                     available providers (OpenAI + Anthropic).
        """
        if clients is not None:
            self._clients = clients
        else:
            self._clients = self._auto_detect_clients()

        self._parser = ResponseParser()

    def _auto_detect_clients(self) -> list[BaseLLMClient]:
        """Auto-detect available LLM clients."""
        clients = []
        openai = OpenAIClient()
        if openai.is_available:
            clients.append(openai)
        anthropic = AnthropicClient()
        if anthropic.is_available:
            clients.append(anthropic)
        return clients

    async def verify(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> VerificationResult:
        """Send prompt to all providers and compare responses.

        Args:
            prompt: User prompt text.
            system_prompt: Optional system instruction.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.

        Returns:
            VerificationResult with agreement score and consensus.
        """
        if not self._clients:
            raise LLMProviderError("No LLM providers available for verification")

        # Call all providers concurrently
        tasks = [
            self._safe_call(client, prompt, system_prompt, max_tokens, temperature)
            for client in self._clients
        ]
        results = await asyncio.gather(*tasks)

        # Parse signals from each response
        signals = []
        responses = []
        for client, result in zip(self._clients, results):
            if result is not None:
                content = result.get("content", "")
                parsed = self._parser.parse_signal_response(content)
                signals.append(parsed.get("signal", "neutral"))
                responses.append({
                    "provider": client.provider_name,
                    "model": client.model,
                    "content": content[:500],
                    "signal": parsed.get("signal", "neutral"),
                    "confidence": parsed.get("confidence", 0.0),
                    "error": None,
                })
            else:
                responses.append({
                    "provider": client.provider_name,
                    "model": client.model,
                    "content": "",
                    "signal": "neutral",
                    "confidence": 0.0,
                    "error": "Provider call failed",
                })

        # Calculate agreement
        agreement = self._calculate_agreement(signals)
        consensus = self._consensus_signal(signals)

        details = {
            "num_providers": len(self._clients),
            "num_responses": len([r for r in responses if r.get("content")]),
            "signal_distribution": self._signal_distribution(signals),
        }

        return VerificationResult(
            responses=responses,
            agreement=agreement,
            consensus_signal=consensus,
            details=details,
        )

    async def _safe_call(
        self,
        client: BaseLLMClient,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> Optional[dict[str, Any]]:
        """Safely call an LLM client, returning None on failure."""
        try:
            return await client.complete(prompt, system_prompt, max_tokens, temperature)
        except Exception as e:
            logger.warning(f"LLM provider {client.provider_name} failed: {e}")
            return None

    def _calculate_agreement(self, signals: list[str]) -> float:
        """Calculate agreement score (0.0-1.0) from signal list.

        1.0 = all agree, 0.0 = complete disagreement.
        """
        if not signals:
            return 0.0

        from collections import Counter
        counts = Counter(signals)
        most_common_count = counts.most_common(1)[0][1]
        return most_common_count / len(signals)

    def _consensus_signal(self, signals: list[str]) -> str:
        """Determine consensus signal from multiple responses."""
        if not signals:
            return "neutral"

        from collections import Counter
        counts = Counter(signals)
        return counts.most_common(1)[0][0]

    def _signal_distribution(self, signals: list[str]) -> dict[str, int]:
        """Get signal distribution."""
        from collections import Counter
        return dict(Counter(signals))
