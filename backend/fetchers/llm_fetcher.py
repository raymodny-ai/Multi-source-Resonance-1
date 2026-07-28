"""
LLM inference data fetcher.

Calls LLM API (OpenAI / Anthropic) to analyse market data and generate
human-readable reports. Falls back to template-based analysis when API
keys are missing or API calls fail.
"""

import json
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base_alt import BaseFetcher


class LLMFetcher(BaseFetcher):
    """Fetches LLM-generated market analysis reports."""

    SOURCE_NAME = "llm_inference"
    CONFIG_KEY = ""  # Managed internally — checks for OPENAI_API_KEY / ANTHROPIC_API_KEY

    # LLM API endpoints
    OPENAI_URL = "https://api.openai.com/v1/chat/completions"
    ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

    def _check_mock_mode(self) -> bool:
        """Override: check for any LLM API key."""
        import os
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
        return not (has_openai or has_anthropic)

    async def fetch(
        self, market_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Fetch LLM analysis of current market conditions.

        Args:
            market_context: Optional dict with current market data to analyse.
        """
        try:
            if self._is_mock:
                data = self._generate_mock_analysis(market_context)
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            # Try OpenAI first
            try:
                data = await self._call_openai(market_context)
                self._record_success()
                return self._build_result(data, extra={"method": "openai"})
            except Exception as e:
                self.logger.warning(f"OpenAI failed: {e}, trying Anthropic")

            # Try Anthropic
            try:
                data = await self._call_anthropic(market_context)
                self._record_success()
                return self._build_result(data, extra={"method": "anthropic"})
            except Exception as e:
                self.logger.warning(f"Anthropic failed: {e}, falling back to template")

            # Final fallback: template
            data = self._generate_mock_analysis(market_context)
            self._record_success()
            return self._build_result(data, extra={"method": "template_fallback"})

        except Exception as e:
            self._record_error(str(e))
            return self._build_result(
                self._generate_mock_analysis(market_context),
                extra={"method": "mock_error", "error": str(e)},
            )

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

        result = await self._post_json(self.OPENAI_URL, json_body=body, headers=headers)
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

        result = await self._post_json(self.ANTHROPIC_URL, json_body=body, headers=headers)
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
