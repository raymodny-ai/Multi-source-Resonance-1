"""
LLM inference data fetcher — compatibility layer.

This module re-exports the LLM inference functionality from the new
backend/llm_inference/ package while maintaining the original
LLMFetcher interface for backward compatibility.

New code should import directly from backend.llm_inference:
    from backend.llm_inference import get_default_client, PromptBuilder
"""

import json
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class LLMFetcher(BaseFetcher):
    """Fetches LLM-generated market analysis reports.

    Now delegates to the backend.llm_inference package for actual
    LLM API calls. Maintains the BaseFetcher interface for pipeline
    integration.
    """

    @property
    def source_name(self) -> str:
        return "llm_inference"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # Managed internally — checks for OPENAI_API_KEY / ANTHROPIC_API_KEY

    def _is_mock_mode(self) -> bool:
        """Override: check for any LLM API key."""
        import os
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
        return not (has_openai or has_anthropic)

    async def fetch(
        self, market_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Fetch LLM analysis of current market conditions."""
        # Try using the new llm_inference package
        try:
            return await self._call_via_package(market_context)
        except Exception as e:
            self.logger.warning(f"llm_inference package failed: {e}, trying direct API")

        # Fallback: direct OpenAI call
        try:
            return await self._call_openai(market_context)
        except Exception as e:
            self.logger.warning(f"OpenAI failed: {e}, trying Anthropic")

        # Fallback: direct Anthropic call
        try:
            return await self._call_anthropic(market_context)
        except Exception as e:
            self.logger.warning(f"Anthropic failed: {e}, falling back to template")

        # Final fallback: template
        return self._generate_mock_analysis(market_context)

    def _mock_data(self) -> dict:
        """Return mock LLM analysis."""
        return self._generate_mock_analysis(None)

    async def _call_via_package(self, context: Optional[dict]) -> dict[str, Any]:
        """Call LLM via the new llm_inference package."""
        from backend.llm_inference import get_default_client, PromptBuilder, ResponseParser

        client = get_default_client()
        builder = PromptBuilder()

        # Build prompt from context
        if context:
            prompt = builder.build_signal_prompt(context)
            system_prompt = builder.get_system_prompt("signal")
        else:
            prompt = "Provide a brief market regime assessment."
            system_prompt = builder.get_system_prompt("regime")

        # Call LLM
        result = await client.complete(prompt, system_prompt=system_prompt)
        content = result.get("content", "")

        # Parse response
        parser = ResponseParser()
        parsed = parser.parse_signal_response(content)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": result.get("provider", client.provider_name),
            "model": result.get("model", client.model),
            "analysis": content,
            "signal": parsed.get("signal", "neutral"),
            "confidence": parsed.get("confidence", 0.5),
            "key_levels": parsed.get("key_levels", {}),
        }

    async def _call_openai(self, context: Optional[dict]) -> dict[str, Any]:
        """Call OpenAI API for market analysis."""
        import os

        prompt = self._build_prompt(context)
        headers = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a quantitative financial analyst. Provide concise market analysis."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        }

        result = await self._post_json(
            "https://api.openai.com/v1/chat/completions",
            json_body=body,
            headers=headers,
        )
        content = result["choices"][0]["message"]["content"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "openai",
            "model": "gpt-4o",
            "analysis": content,
            "signal": self._extract_signal(content),
            "confidence": round(random.uniform(0.6, 0.9), 2),
        }

    async def _call_anthropic(self, context: Optional[dict]) -> dict[str, Any]:
        """Call Anthropic API for market analysis."""
        import os

        prompt = self._build_prompt(context)
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        result = await self._post_json(
            "https://api.anthropic.com/v1/messages",
            json_body=body,
            headers=headers,
        )
        content = result["content"][0]["text"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "analysis": content,
            "signal": self._extract_signal(content),
            "confidence": round(random.uniform(0.6, 0.9), 2),
        }

    def _build_prompt(self, context: Optional[dict]) -> str:
        """Build the analysis prompt from market context."""
        if context:
            context_str = json.dumps(context, indent=2, default=str)
        else:
            context_str = "No specific market data provided."

        return f"""Analyse the following multi-source resonance monitoring data and provide:
1. Current market regime assessment
2. Key risk factors
3. Resonance signal interpretation
4. Recommended action (if any)

Market Data:
{context_str}

Keep response under 200 words. Be specific and quantitative."""

    def _extract_signal(self, analysis: str) -> str:
        """Extract a simple signal label from analysis text."""
        analysis_lower = analysis.lower()
        if any(w in analysis_lower for w in ["buy", "accumulation", "bottom", "bullish"]):
            return "bullish"
        elif any(w in analysis_lower for w in ["sell", "distribution", "top", "bearish"]):
            return "bearish"
        return "neutral"

    def _generate_mock_analysis(self, context: Optional[dict]) -> dict[str, Any]:
        """Generate preset mock analysis result."""
        signals = ["bullish", "bearish", "neutral"]
        regimes = [
            "Risk-on regime with moderate GEX support",
            "Negative gamma environment — elevated volatility expected",
            "Transitioning from fear to neutral — watch zero gamma level",
            "Liquidity cascade exhaustion detected — potential bottom forming",
            "Normal market conditions — no strong resonance signal",
        ]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "mock",
            "model": "template-v1",
            "analysis": random.choice(regimes),
            "signal": random.choice(signals),
            "confidence": round(random.uniform(0.4, 0.7), 2),
            "key_levels": {
                "support": round(random.uniform(5200, 5400), 0),
                "resistance": round(random.uniform(5600, 5800), 0),
                "zero_gamma": round(random.uniform(5450, 5550), 0),
            },
        }
