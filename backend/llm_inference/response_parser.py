"""
LLM response parser — structured JSON extraction from LLM outputs.

Parses free-text LLM responses into structured dicts:
- Signal extraction (bullish/bearish/neutral)
- Confidence score extraction
- Key level extraction
- Hallucination detection (v2.6)
"""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse LLM responses into structured data.

    Usage:
        parser = ResponseParser()
        result = parser.parse_signal_response(llm_content)
    """

    # Signal keywords for extraction
    BULLISH_KEYWORDS = ["buy", "accumulation", "bottom", "bullish", "long", "upside", "recovery"]
    BEARISH_KEYWORDS = ["sell", "distribution", "top", "bearish", "short", "downside", "risk-off"]
    NEUTRAL_KEYWORDS = ["neutral", "sideways", "wait", "observe", "cautious"]

    def parse_signal_response(self, content: str) -> dict[str, Any]:
        """Parse a signal analysis response.

        Args:
            content: Raw LLM response text.

        Returns:
            Structured dict with signal, confidence, key_levels, summary.
        """
        signal = self._extract_signal(content)
        confidence = self._extract_confidence(content)
        key_levels = self._extract_key_levels(content)
        summary = self._extract_summary(content)

        return {
            "signal": signal,
            "confidence": confidence,
            "key_levels": key_levels,
            "summary": summary,
            "raw_length": len(content),
        }

    def parse_incident_response(self, content: str) -> dict[str, Any]:
        """Parse an incident analysis response.

        Args:
            content: Raw LLM response text.

        Returns:
            Structured dict with severity, root_cause, actions, monitoring.
        """
        severity = self._extract_severity(content)
        actions = self._extract_actions(content)
        root_cause = self._extract_root_cause(content)

        return {
            "severity": severity,
            "root_cause": root_cause,
            "recommended_actions": actions,
            "summary": content[:500],
            "raw_length": len(content),
        }

    def parse_json_response(self, content: str) -> Optional[dict[str, Any]]:
        """Attempt to extract JSON from LLM response.

        Handles cases where LLM wraps JSON in markdown code blocks.

        Args:
            content: Raw LLM response text.

        Returns:
            Parsed JSON dict, or None if extraction fails.
        """
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON-like structure
        brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to extract JSON from LLM response")
        return None

    def detect_hallucination(self, content: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Detect potential hallucination in LLM response.

        Checks if LLM mentions values/facts not present in input data.

        Args:
            content: LLM response text.
            input_data: Original input data sent to LLM.

        Returns:
            dict with 'is_suspect', 'reasons', 'score' keys.
        """
        reasons = []
        suspect_score = 0.0

        # Check for specific price levels not in input
        input_str = json.dumps(input_data, default=str)
        numbers_in_response = re.findall(r"\b\d{3,5}(?:\.\d+)?\b", content)

        for num_str in numbers_in_response:
            if num_str not in input_str:
                suspect_score += 0.1
                reasons.append(f"Unverified number in response: {num_str}")

        # Check for contradictory signals
        has_bullish = any(kw in content.lower() for kw in self.BULLISH_KEYWORDS)
        has_bearish = any(kw in content.lower() for kw in self.BEARISH_KEYWORDS)
        if has_bullish and has_bearish:
            suspect_score += 0.2
            reasons.append("Contradictory bullish and bearish signals")

        # Cap score at 1.0
        suspect_score = min(suspect_score, 1.0)

        return {
            "is_suspect": suspect_score > 0.3,
            "score": round(suspect_score, 2),
            "reasons": reasons[:5],  # Limit to top 5 reasons
        }

    def _extract_signal(self, content: str) -> str:
        """Extract signal label from text."""
        content_lower = content.lower()
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in content_lower)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in content_lower)

        if bullish_count > bearish_count + 1:
            return "bullish"
        elif bearish_count > bullish_count + 1:
            return "bearish"
        return "neutral"

    def _extract_confidence(self, content: str) -> float:
        """Extract confidence score from text."""
        # Look for explicit percentage or decimal
        pct_match = re.search(r"confidence[:\s]*(\d+(?:\.\d+)?)\s*%", content, re.IGNORECASE)
        if pct_match:
            return round(float(pct_match.group(1)) / 100.0, 2)

        dec_match = re.search(r"confidence[:\s]*(0\.\d+)", content, re.IGNORECASE)
        if dec_match:
            return round(float(dec_match.group(1)), 2)

        # Infer from language strength
        strong_words = ["definitely", "certainly", "clearly", "strong"]
        weak_words = ["possibly", "might", "could", "uncertain"]

        strong_count = sum(1 for w in strong_words if w in content.lower())
        weak_count = sum(1 for w in weak_words if w in content.lower())

        if strong_count > weak_count:
            return 0.75
        elif weak_count > strong_count:
            return 0.45
        return 0.6

    def _extract_key_levels(self, content: str) -> dict[str, float]:
        """Extract key price levels from text."""
        levels = {}

        # Look for patterns like "support at 5400" or "resistance: 5600"
        level_patterns = [
            (r"support[:\s]*(?:at\s+)?(\d{3,5})", "support"),
            (r"resistance[:\s]*(?:at\s+)?(\d{3,5})", "resistance"),
            (r"zero[_\s]gamma[:\s]*(?:at\s+)?(\d{3,5})", "zero_gamma"),
            (r"target[:\s]*(?:at\s+)?(\d{3,5})", "target"),
        ]

        for pattern, key in level_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                levels[key] = float(match.group(1))

        return levels

    def _extract_summary(self, content: str) -> str:
        """Extract a concise summary from the response."""
        # Take first paragraph or first 200 chars
        paragraphs = content.strip().split("\n\n")
        if paragraphs:
            return paragraphs[0][:300]
        return content[:300]

    def _extract_severity(self, content: str) -> str:
        """Extract severity assessment."""
        content_lower = content.lower()
        if any(w in content_lower for w in ["critical", "severe", "extreme", "emergency"]):
            return "critical"
        elif any(w in content_lower for w in ["high", "significant", "elevated"]):
            return "high"
        elif any(w in content_lower for w in ["moderate", "medium"]):
            return "moderate"
        return "low"

    def _extract_actions(self, content: str) -> list[str]:
        """Extract recommended actions from text."""
        actions = []
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "•", "*")) or re.match(r"^\d+[.)]\s", line):
                # Clean up list item
                cleaned = re.sub(r"^[-•*\d.)]+\s*", "", line).strip()
                if cleaned and len(cleaned) > 5:
                    actions.append(cleaned)
        return actions[:5]

    def _extract_root_cause(self, content: str) -> str:
        """Extract root cause statement."""
        # Look for "root cause" or "cause" section
        match = re.search(r"(?:root\s+)?cause[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]
        return content[:200]
