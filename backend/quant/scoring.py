"""
Four-dimensional resonance scoring engine (core).
Computes weighted scores across GEX, VIX, Crypto, and Darkpool dimensions,
with normalization to 0-100 range and signal level determination.

Weight allocation (raw total = 8.0 max):
  - GEX:      2.5 points (31.25% of 8.0)
  - VIX:      1.5 points (18.75% of 8.0)
  - Crypto:   2.0 points (25.00% of 8.0)
  - Darkpool: 2.0 points (25.00% of 8.0)

Normalization: raw_score / 8.0 * 100 → 0-100 range

Signal levels (on normalized 0-100 scale):
  - LEVEL_0: 0-25   (no signal)
  - LEVEL_1: 25-50  (weak signal)
  - LEVEL_2: 50-75  (moderate signal)
  - LEVEL_3: 75-100 (strong signal)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Default dimension weights (raw max = 8.0 total)
DEFAULT_WEIGHTS = {
    "gex": 2.5,
    "vix": 1.5,
    "crypto": 2.0,
    "darkpool": 2.0,
}

# Backward-compatible alias
WEIGHTS = DEFAULT_WEIGHTS

RAW_MAX = sum(DEFAULT_WEIGHTS.values())  # 8.0

# ── Dynamic weight management via BayesianWeightAdapter ──────────────────────
_adapter_instance: Optional[object] = None  # Lazy-initialized BayesianWeightAdapter


def _get_adapter():
    """Lazily initialise and return the module-level BayesianWeightAdapter."""
    global _adapter_instance
    if _adapter_instance is None:
        # Lazy import to avoid circular dependency (bayesian_weights imports scoring)
        from backend.quant.bayesian_weights import BayesianWeightAdapter
        _adapter_instance = BayesianWeightAdapter()
        logger.info("BayesianWeightAdapter initialised")
    return _adapter_instance


def get_current_weights() -> dict:
    """Return current dimension weights.

    If the BayesianWeightAdapter has been updated with signal outcomes,
    returns the dynamically adapted weights. Otherwise returns defaults.
    """
    try:
        if _adapter_instance is not None:
            stats = _adapter_instance.get_update_stats()
            if stats["update_count"] > 0:
                weights = _adapter_instance.get_current_weights()
                # Sanity check: weights should sum to RAW_MAX
                if abs(sum(weights.values()) - RAW_MAX) < 0.01:
                    return weights
    except Exception as exc:
        logger.warning(f"Failed to get dynamic weights, using defaults: {exc}")
    return dict(DEFAULT_WEIGHTS)


def reset_weights() -> None:
    """Reset dynamic weights back to defaults."""
    global _adapter_instance
    if _adapter_instance is not None:
        _adapter_instance.reset()
    logger.info("Scoring weights reset to defaults")

# Level thresholds on normalized 0-100 scale
LEVEL_THRESHOLDS = {
    "LEVEL_0": (0.0, 25.0),
    "LEVEL_1": (25.0, 50.0),
    "LEVEL_2": (50.0, 75.0),
    "LEVEL_3": (75.0, 100.0),
}

_DEFAULT_RESULT = {
    "normalized_score": 0.0,
    "raw_score": 0.0,
    "raw_max": RAW_MAX,
    "level": "LEVEL_0",
    "dimension_scores": {
        "gex": 0.0,
        "vix": 0.0,
        "crypto": 0.0,
        "darkpool": 0.0,
    },
    "dimension_weights": WEIGHTS,
    "signals": [],
    "timestamp": None,
}


def calculate_score(
    gex_score: float = 0.0,
    vix_score: float = 0.0,
    crypto_score: float = 0.0,
    darkpool_score: float = 0.0,
) -> dict:
    """Calculate four-dimensional resonance score.

    Each dimension score is expected in 0-100 range (from individual analyzers).
    The scoring works as follows:
    1. Each dimension contributes proportionally to its weight:
       dimension_contribution = (dimension_score / 100) * dimension_weight
    2. Raw total = sum of contributions (max = 8.0)
    3. Normalized score = (raw_total / 8.0) * 100 → 0-100 range

    Args:
        gex_score: GEX dimension score (0-100)
        vix_score: VIX dimension score (0-100)
        crypto_score: Crypto dimension score (0-100)
        darkpool_score: Darkpool dimension score (0-100)

    Returns:
        dict with normalized_score, raw_score, level, dimension_scores, signals, timestamp
    """
    try:
        # Clamp individual scores to 0-100
        gex_score = max(0.0, min(100.0, gex_score))
        vix_score = max(0.0, min(100.0, vix_score))
        crypto_score = max(0.0, min(100.0, crypto_score))
        darkpool_score = max(0.0, min(100.0, darkpool_score))

        # Use dynamic weights (falls back to defaults if no adapter data)
        weights = get_current_weights()

        # Calculate weighted contributions (each dimension contributes up to its weight)
        gex_contrib = (gex_score / 100.0) * weights["gex"]
        vix_contrib = (vix_score / 100.0) * weights["vix"]
        crypto_contrib = (crypto_score / 100.0) * weights["crypto"]
        darkpool_contrib = (darkpool_score / 100.0) * weights["darkpool"]

        # Raw score (max = 8.0)
        raw_score = gex_contrib + vix_contrib + crypto_contrib + darkpool_contrib

        # Normalize to 0-100
        normalized_score = (raw_score / RAW_MAX) * 100.0

        # Determine level
        level = determine_level(normalized_score)

        # Collect dimension signals
        signals = []
        if gex_score >= 75:
            signals.append("gex_strong")
        elif gex_score >= 50:
            signals.append("gex_moderate")

        if vix_score >= 75:
            signals.append("vix_strong")
        elif vix_score >= 50:
            signals.append("vix_moderate")

        if crypto_score >= 75:
            signals.append("crypto_strong")
        elif crypto_score >= 50:
            signals.append("crypto_moderate")

        if darkpool_score >= 75:
            signals.append("darkpool_strong")
        elif darkpool_score >= 50:
            signals.append("darkpool_moderate")

        # Resonance bonus: if 3+ dimensions are strong, boost
        strong_count = sum(
            1 for s in [gex_score, vix_score, crypto_score, darkpool_score]
            if s >= 60
        )
        if strong_count >= 3:
            signals.append("multi_dimension_resonance")
            # Add a small resonance bonus (up to 10 points)
            resonance_bonus = (strong_count - 2) * 5.0
            normalized_score = min(100.0, normalized_score + resonance_bonus)
            # Re-evaluate level after bonus
            level = determine_level(normalized_score)

        return {
            "normalized_score": round(normalized_score, 2),
            "raw_score": round(raw_score, 4),
            "raw_max": RAW_MAX,
            "level": level,
            "dimension_scores": {
                "gex": round(gex_score, 2),
                "vix": round(vix_score, 2),
                "crypto": round(crypto_score, 2),
                "darkpool": round(darkpool_score, 2),
            },
            "dimension_weights": weights,
            "signals": signals,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Score calculation failed: {e}", exc_info=True)
        import copy
        result = copy.deepcopy(_DEFAULT_RESULT)
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result


def determine_level(normalized_score: float) -> str:
    """Determine signal level from normalized score (0-100).

    Args:
        normalized_score: Score in 0-100 range.

    Returns:
        Signal level string: 'LEVEL_0' | 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3'
    """
    if normalized_score >= 75.0:
        return "LEVEL_3"
    elif normalized_score >= 50.0:
        return "LEVEL_2"
    elif normalized_score >= 25.0:
        return "LEVEL_1"
    return "LEVEL_0"


def calculate_score_from_analyses(
    gex_result: dict,
    vix_result: dict,
    crypto_result: dict,
    darkpool_result: dict,
) -> dict:
    """Convenience function to calculate score from analyzer result dicts.

    Args:
        gex_result: Output from gex_analyzer.analyze()
        vix_result: Output from vix_analyzer.analyze()
        crypto_result: Output from crypto_analyzer.analyze()
        darkpool_result: Output from darkpool_analyzer.analyze()

    Returns:
        Scoring result dict from calculate_score()
    """
    return calculate_score(
        gex_score=gex_result.get("score", 0.0),
        vix_score=vix_result.get("score", 0.0),
        crypto_score=crypto_result.get("score", 0.0),
        darkpool_score=darkpool_result.get("score", 0.0),
    )


def get_dimension_summary(scoring_result: dict) -> dict:
    """Extract a human-readable summary from scoring result.

    Args:
        scoring_result: Output from calculate_score()

    Returns:
        dict with human-readable summary
    """
    level = scoring_result.get("level", "LEVEL_0")
    normalized = scoring_result.get("normalized_score", 0.0)
    dims = scoring_result.get("dimension_scores", {})
    weights_used = scoring_result.get("dimension_weights", DEFAULT_WEIGHTS)

    level_descriptions = {
        "LEVEL_0": "No signal — market conditions normal",
        "LEVEL_1": "Weak signal — early stage monitoring",
        "LEVEL_2": "Moderate signal — increased vigilance",
        "LEVEL_3": "Strong signal — multi-dimension resonance detected",
    }

    return {
        "level": level,
        "level_description": level_descriptions.get(level, "Unknown"),
        "normalized_score": normalized,
        "dimensions": {
            f"GEX (weight {weights_used.get('gex', 2.5):.2f})": f"{dims.get('gex', 0):.1f}/100",
            f"VIX (weight {weights_used.get('vix', 1.5):.2f})": f"{dims.get('vix', 0):.1f}/100",
            f"Crypto (weight {weights_used.get('crypto', 2.0):.2f})": f"{dims.get('crypto', 0):.1f}/100",
            f"Darkpool (weight {weights_used.get('darkpool', 2.0):.2f})": f"{dims.get('darkpool', 0):.1f}/100",
        },
        "signals": scoring_result.get("signals", []),
    }
