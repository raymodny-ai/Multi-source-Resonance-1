"""
Put/Call ratio analyzer module.
Analyzes put/call ratio to detect extreme market sentiment.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "put_call_ratio": None,
        "ratio_type": "unknown",
        "percentile": None,
        "extreme_reading": False,
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze put/call ratio data and return score, level, signals, and details.

    Args:
        data: Put/Call data dict. Expected keys:
            - put_call_ratio: float — current P/C ratio
            - pc_ratio_20d_avg: float — 20-day average P/C ratio
            - pc_ratio_percentile: float — percentile rank (0-100)
            - ratio_type: str — 'equity' | 'index' | 'total'

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_put_call_analysis(data)
    except Exception as e:
        logger.error(f"Put/Call analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_put_call_analysis(data: dict) -> dict:
    """Core put/call analysis computation."""
    pc_ratio = data.get("put_call_ratio")
    pc_avg = data.get("pc_ratio_20d_avg")
    percentile = data.get("pc_ratio_percentile")
    ratio_type = data.get("ratio_type", "total")

    signals = []
    raw_score = 0.0

    if pc_ratio is not None:
        # High put/call ratio = extreme fear = contrarian bullish
        if pc_ratio > 1.5:
            signals.append("extreme_put_call_high")
            raw_score += 60.0
        elif pc_ratio > 1.2:
            signals.append("elevated_put_call")
            raw_score += 40.0
        elif pc_ratio > 1.0:
            signals.append("above_neutral_put_call")
            raw_score += 20.0
        elif pc_ratio < 0.5:
            signals.append("extreme_low_put_call")
            # Very low put/call = complacency = less signal for bottom
            raw_score += 5.0

        # Percentile-based scoring
        if percentile is not None:
            if percentile > 90:
                signals.append("pc_percentile_extreme_high")
                raw_score += 30.0
            elif percentile > 75:
                signals.append("pc_percentile_high")
                raw_score += 15.0

        # Deviation from average
        if pc_avg and pc_avg > 0:
            deviation = (pc_ratio - pc_avg) / pc_avg
            if deviation > 0.3:
                signals.append("pc_above_average")
                raw_score += 20.0

    extreme_reading = pc_ratio is not None and pc_ratio > 1.3

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "put_call_ratio": pc_ratio,
            "ratio_type": ratio_type,
            "percentile": percentile,
            "extreme_reading": extreme_reading,
        },
    }


def _score_to_level(score: float) -> str:
    """Convert numeric score to signal level."""
    if score >= 75.0:
        return "LEVEL_3"
    elif score >= 50.0:
        return "LEVEL_2"
    elif score >= 25.0:
        return "LEVEL_1"
    return "LEVEL_0"
