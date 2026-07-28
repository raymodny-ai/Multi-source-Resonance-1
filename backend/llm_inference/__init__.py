"""
LLM inference package — Layer3 of the V2.0 three-layer decoupled architecture.

Provides:
- BaseLLMClient / OpenAIClient / AnthropicClient: Provider abstraction
- PromptBuilder: Structured prompt templates with anonymization
- ResponseParser: JSON extraction and signal parsing from LLM outputs
- LLMCache: SQLite-backed result caching (2s → 50ms for cache hits)
- MultiLLMVerifier: Cross-verification across GPT-4o + Claude
- ConfidenceScorer: Output confidence scoring with hallucination detection

Usage:
    from backend.llm_inference import get_default_client, PromptBuilder
    client = get_default_client()
    builder = PromptBuilder()
    prompt = builder.build_signal_prompt(scores_data)
    result = await client.complete(prompt, system_prompt=builder.get_system_prompt("signal"))
"""

from backend.llm_inference.base import (
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    LLMProviderError,
    get_default_client,
)
from backend.llm_inference.prompt_builder import PromptBuilder, SYSTEM_PROMPTS
from backend.llm_inference.response_parser import ResponseParser
from backend.llm_inference.cache import LLMCache, get_cache
from backend.llm_inference.multi_verify import MultiLLMVerifier, VerificationResult
from backend.llm_inference.confidence import ConfidenceScorer

__all__ = [
    # Base clients
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "LLMProviderError",
    "get_default_client",
    # Prompt
    "PromptBuilder",
    "SYSTEM_PROMPTS",
    # Parser
    "ResponseParser",
    # Cache
    "LLMCache",
    "get_cache",
    # Multi-verify
    "MultiLLMVerifier",
    "VerificationResult",
    # Confidence
    "ConfidenceScorer",
]
