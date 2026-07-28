"""
Prompt template builder for LLM inference.

Constructs structured prompts for different analysis types:
- Signal analysis (resonance scoring interpretation)
- Incident report (LEVEL_3 alert explanation)
- Market regime assessment
- Multi-asset correlation summary
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# System prompts for different analysis types
SYSTEM_PROMPTS = {
    "signal": (
        "You are a quantitative financial analyst specializing in multi-source "
        "resonance signal detection. Analyze the provided market data and scoring "
        "metrics. Be specific, quantitative, and concise (under 200 words)."
    ),
    "incident": (
        "You are a senior risk analyst. A LEVEL_3 resonance alert has been triggered. "
        "Explain the incident, assess the risk, and recommend action. "
        "Be precise and actionable (under 300 words)."
    ),
    "regime": (
        "You are a market regime analyst. Assess the current market environment "
        "based on GEX, VIX term structure, crypto leverage, and dark pool flows. "
        "Identify the regime (risk-on, risk-off, transition) and key drivers."
    ),
    "summary": (
        "You are a financial data analyst. Summarize the multi-asset market data "
        "into a concise report highlighting key signals and cross-asset correlations."
    ),
}


class PromptBuilder:
    """Builds structured prompts for LLM analysis.

    Usage:
        builder = PromptBuilder()
        prompt = builder.build_signal_prompt(scores_data, context)
    """

    def __init__(self, anonymize: bool = True) -> None:
        """Initialize prompt builder.

        Args:
            anonymize: If True, replace specific tickers with generic labels
                       to prevent LLM hallucination (v2.6 feature).
        """
        self._anonymize = anonymize
        self._ticker_map = {
            "SPX": "Asset_A",
            "SPY": "Asset_B",
            "QQQ": "Asset_C",
            "IWM": "Asset_D",
            "NDX": "Asset_E",
            "VIX": "Volatility_Index",
        }

    def build_signal_prompt(
        self,
        scores: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Build prompt for resonance signal analysis.

        Args:
            scores: Dimension scores (gex_score, vix_score, etc.)
            context: Additional market context data.

        Returns:
            Formatted prompt string.
        """
        scores_str = self._format_data(scores)
        context_str = self._format_data(context) if context else "No additional context."

        return f"""Analyse the following multi-source resonance scoring data:

Dimension Scores:
{scores_str}

Market Context:
{context_str}

Provide:
1. Current signal interpretation (bullish/bearish/neutral)
2. Key contributing factors
3. Risk assessment
4. Recommended action

Keep response under 200 words. Be quantitative."""

    def build_incident_prompt(
        self,
        incident: dict[str, Any],
        scores: dict[str, Any],
    ) -> str:
        """Build prompt for LEVEL_3 incident analysis.

        Args:
            incident: Incident details (alert_level, total_score, etc.)
            scores: Full dimension score breakdown.

        Returns:
            Formatted prompt string.
        """
        incident_str = self._format_data(incident)
        scores_str = self._format_data(scores)

        return f"""A LEVEL_3 resonance incident has been triggered.

Incident Details:
{incident_str}

Score Breakdown:
{scores_str}

Provide:
1. Root cause analysis
2. Severity assessment
3. Historical comparison (if applicable)
4. Recommended immediate action
5. Monitoring recommendations

Be precise and actionable. Under 300 words."""

    def build_regime_prompt(
        self,
        market_data: dict[str, Any],
    ) -> str:
        """Build prompt for market regime assessment.

        Args:
            market_data: Multi-dimensional market data.

        Returns:
            Formatted prompt string.
        """
        data_str = self._format_data(market_data)

        return f"""Assess the current market regime based on the following data:

{data_str}

Provide:
1. Regime classification (risk-on / risk-off / transition)
2. Key drivers
3. GEX environment (positive/negative gamma)
4. Volatility outlook
5. Cross-asset correlation assessment

Under 250 words."""

    def _format_data(self, data: dict[str, Any]) -> str:
        """Format data dict for prompt inclusion.

        Applies anonymization if enabled.
        """
        if self._anonymize:
            data = self._anonymize_data(data)

        return json.dumps(data, indent=2, default=str)

    def _anonymize_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Replace specific ticker symbols with generic labels.

        Prevents LLM from hallucinating based on known ticker behavior.
        """
        data_str = json.dumps(data, default=str)
        for ticker, label in self._ticker_map.items():
            data_str = data_str.replace(f'"{ticker}"', f'"{label}"')
            data_str = data_str.replace(f"'{ticker}'", f"'{label}'")
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return data

    def get_system_prompt(self, analysis_type: str) -> str:
        """Get the system prompt for a given analysis type.

        Args:
            analysis_type: One of 'signal', 'incident', 'regime', 'summary'.

        Returns:
            System prompt string.
        """
        return SYSTEM_PROMPTS.get(analysis_type, SYSTEM_PROMPTS["summary"])
