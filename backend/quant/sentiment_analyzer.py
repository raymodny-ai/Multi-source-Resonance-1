"""
Sentiment analyzer module.
Analyzes market sentiment indicators including fear/greed index.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "fear_greed_index": None,
        "sentiment_label": "neutral",
        "sentiment_bias": "neutral",
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze sentiment data and return score, level, signals, and details.

    Args:
        data: Sentiment data dict. Expected keys:
            - fear_greed_index: float — CNN Fear & Greed Index (0-100)
            - put_call_ratio: float — put/call ratio
            - vix_level: float — VIX current level
            - market_breadth: float — advance/decline ratio
            - sentiment_sources: dict — various sentiment readings

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_sentiment_analysis(data)
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_sentiment_analysis(data: dict) -> dict:
    """Core sentiment analysis computation."""
    fg_index = data.get("fear_greed_index")
    pc_ratio = data.get("put_call_ratio")
    vix_level = data.get("vix_level")
    breadth = data.get("market_breadth")

    signals = []
    raw_score = 0.0

    # --- Fear & Greed Index ---
    if fg_index is not None:
        if fg_index < 20:
            signals.append("extreme_fear")
            raw_score += 50.0  # Extreme fear = contrarian bullish
        elif fg_index < 35:
            signals.append("fear")
            raw_score += 30.0
        elif fg_index < 50:
            signals.append("neutral_to_fear")
            raw_score += 15.0
        elif fg_index > 80:
            signals.append("extreme_greed")
            # Extreme greed = contrarian bearish, reduce score
            raw_score += 5.0

    # --- Put/Call Ratio ---
    if pc_ratio is not None:
        if pc_ratio > 1.2:
            signals.append("high_pc_ratio")
            raw_score += 25.0  # High put/call = fear = contrarian bullish
        elif pc_ratio > 1.0:
            signals.append("elevated_pc_ratio")
            raw_score += 15.0

    # --- VIX level ---
    if vix_level is not None:
        if vix_level > 30:
            signals.append("high_vix")
            raw_score += 20.0
        elif vix_level > 25:
            signals.append("elevated_vix")
            raw_score += 10.0

    # --- Market breadth ---
    if breadth is not None:
        if breadth < 0.3:
            signals.append("weak_breadth")
            raw_score += 15.0  # Weak breadth can signal oversold

    # Determine sentiment label
    sentiment_label = "neutral"
    if fg_index is not None:
        if fg_index < 25:
            sentiment_label = "extreme_fear"
        elif fg_index < 45:
            sentiment_label = "fear"
        elif fg_index < 55:
            sentiment_label = "neutral"
        elif fg_index < 75:
            sentiment_label = "greed"
        else:
            sentiment_label = "extreme_greed"

    # Determine bias
    sentiment_bias = "neutral"
    if raw_score >= 40:
        sentiment_bias = "contrarian_bullish"
    elif raw_score >= 20:
        sentiment_bias = "mildly_bullish"
    elif raw_score < 10:
        sentiment_bias = "complacent"

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "fear_greed_index": fg_index,
            "sentiment_label": sentiment_label,
            "sentiment_bias": sentiment_bias,
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
