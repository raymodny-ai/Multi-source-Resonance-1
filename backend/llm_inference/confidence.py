"""
LLM output confidence scoring.

Calculates confidence scores for LLM outputs based on:
- Multi-provider agreement (cross-verification)
- Response consistency (keyword density, specificity)
- Data coverage (how much input data was addressed)
- Hallucination indicators (unverified numbers, contradictions)
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculate confidence scores for LLM outputs.

    Usage:
        scorer = ConfidenceScorer()
        score = scorer.score(response_content, input_data, verification_result)
    """

    # Weights for different confidence factors
    WEIGHTS = {
        "provider_agreement": 0.30,
        "response_specificity": 0.25,
        "data_coverage": 0.20,
        "hallucination_penalty": 0.25,
    }

    def score(
        self,
        content: str,
        input_data: Optional[dict[str, Any]] = None,
        verification: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Calculate overall confidence score for an LLM response.

        Args:
            content: LLM response text.
            input_data: Original input data sent to LLM.
            verification: Multi-provider verification result.

        Returns:
            dict with 'overall', 'factors', and 'flags' keys.
        """
        factors = {}

        # Factor 1: Provider agreement
        if verification and "agreement" in verification:
            factors["provider_agreement"] = verification["agreement"]
        else:
            factors["provider_agreement"] = 0.5  # Neutral if single provider

        # Factor 2: Response specificity
        factors["response_specificity"] = self._score_specificity(content)

        # Factor 3: Data coverage
        if input_data:
            factors["data_coverage"] = self._score_data_coverage(content, input_data)
        else:
            factors["data_coverage"] = 0.5

        # Factor 4: Hallucination penalty (inverted — lower is better)
        hallucination_score = self._score_hallucination(content, input_data or {})
        factors["hallucination_penalty"] = 1.0 - hallucination_score

        # Weighted overall score
        overall = sum(
            factors.get(k, 0.5) * w
            for k, w in self.WEIGHTS.items()
        )

        # Flags
        flags = self._generate_flags(factors, content)

        return {
            "overall": round(overall, 3),
            "factors": {k: round(v, 3) for k, v in factors.items()},
            "flags": flags,
            "confidence_level": self._confidence_level(overall),
        }

    def _score_specificity(self, content: str) -> float:
        """Score how specific and quantitative the response is.

        Higher score for responses with numbers, percentages, and
        specific references rather than vague language.
        """
        if not content:
            return 0.0

        # Count numeric references
        numbers = re.findall(r"\d+(?:\.\d+)?%?", content)
        number_density = len(numbers) / max(len(content.split()), 1)

        # Count specific financial terms
        financial_terms = [
            "gex", "vix", "dix", "gamma", "put", "call", "strike",
            "support", "resistance", "drawdown", "sharpe", "momentum",
            "contango", "backwardation", "funding", "liquidation",
        ]
        term_count = sum(1 for t in financial_terms if t in content.lower())

        # Penalize vague language
        vague_words = ["maybe", "perhaps", "might", "could", "possibly", "unclear"]
        vague_count = sum(1 for w in vague_words if w in content.lower())

        specificity = min(1.0, (number_density * 2 + term_count * 0.1))
        specificity -= vague_count * 0.05

        return max(0.0, min(1.0, specificity))

    def _score_data_coverage(self, content: str, input_data: dict[str, Any]) -> float:
        """Score how much of the input data was addressed in the response.

        Checks if key input fields are mentioned in the response.
        """
        content_lower = content.lower()

        # Extract key terms from input data
        key_terms = self._extract_key_terms(input_data)
        if not key_terms:
            return 0.5  # Neutral if no key terms found

        covered = sum(1 for term in key_terms if term.lower() in content_lower)
        return covered / len(key_terms)

    def _score_hallucination(
        self, content: str, input_data: dict[str, Any]
    ) -> float:
        """Score likelihood of hallucination (0.0 = no hallucination, 1.0 = likely).

        Checks for:
        - Numbers not present in input
        - Contradictory statements
        - Overly confident language without data support
        """
        if not input_data:
            return 0.2  # Low penalty if no input to compare

        score = 0.0
        input_str = str(input_data).lower()

        # Check for specific price levels not in input
        numbers_in_response = re.findall(r"\b\d{4,5}(?:\.\d+)?\b", content)
        for num in numbers_in_response:
            if num not in input_str:
                score += 0.1

        # Check for contradictions
        has_bullish = any(w in content.lower() for w in ["bullish", "buy", "upside"])
        has_bearish = any(w in content.lower() for w in ["bearish", "sell", "downside"])
        if has_bullish and has_bearish:
            score += 0.2

        # Check for overconfidence
        overconfident = ["definitely", "certainly", "will", "guaranteed"]
        if any(w in content.lower() for w in overconfident):
            score += 0.1

        return min(1.0, score)

    def _extract_key_terms(self, data: dict[str, Any]) -> list[str]:
        """Extract key terms from input data for coverage checking."""
        terms = []
        for key in data.keys():
            # Add key names as terms
            term = key.replace("_", " ").replace("score", "").strip()
            if term and len(term) > 2:
                terms.append(term)

        # Add common financial dimension terms
        dimension_terms = ["gex", "vix", "crypto", "darkpool", "dix", "gamma", "funding"]
        for dt in dimension_terms:
            if dt in str(data).lower():
                terms.append(dt)

        return list(set(terms))

    def _generate_flags(self, factors: dict[str, float], content: str) -> list[str]:
        """Generate warning flags based on confidence factors."""
        flags = []

        if factors.get("provider_agreement", 0.5) < 0.5:
            flags.append("LOW_PROVIDER_AGREEMENT")

        if factors.get("response_specificity", 0.5) < 0.3:
            flags.append("LOW_SPECIFICITY")

        if factors.get("hallucination_penalty", 0.5) < 0.5:
            flags.append("POTENTIAL_HALLUCINATION")

        if factors.get("data_coverage", 0.5) < 0.3:
            flags.append("LOW_DATA_COVERAGE")

        # Check for very short response
        if len(content.split()) < 30:
            flags.append("VERY_SHORT_RESPONSE")

        return flags

    def _confidence_level(self, score: float) -> str:
        """Convert numeric score to confidence level."""
        if score >= 0.8:
            return "HIGH"
        elif score >= 0.6:
            return "MEDIUM"
        elif score >= 0.4:
            return "LOW"
        return "VERY_LOW"
