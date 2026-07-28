"""
VIX analyzer module.
Analyzes VIX fear index data, term structure state, and panic premium.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "vix_spot": None,
        "vx1": None,
        "vx2": None,
        "term_structure_ratio": None,
        "term_structure_state": "unknown",
        "panic_premium": None,
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze VIX data and return score, level, signals, and details.

    Args:
        data: VIX data dict from VIX/CBOE fetcher. Expected keys:
            - vix_spot: float — VIX spot price
            - vx1: float — VIX 1-month futures
            - vx2: float — VIX 2-month futures
            - term_structure_ratio: float — (vx2/vx1) - 1
            - term_structure_state: str — 'contango' | 'backwardation' | 'flat'
            - panic_premium: float — panic premium value

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_vix_analysis(data)
    except Exception as e:
        logger.error(f"VIX analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_vix_analysis(data: dict) -> dict:
    """Core VIX analysis computation."""
    vix_spot = data.get("vix_spot")
    vx1 = data.get("vx1")
    vx2 = data.get("vx2")
    ts_ratio = data.get("term_structure_ratio")
    ts_state = data.get("term_structure_state")
    panic_premium = data.get("panic_premium")

    signals = []
    raw_score = 0.0

    # --- Signal 1: Term structure in contango (fear subsiding) ---
    # Weight: max 1.00 points → normalized to 0-66.67 (of 1.5 total weight)
    if ts_state:
        if ts_state == "contango":
            signals.append("term_structure_contango")
            # Stronger contango = higher score
            if ts_ratio is not None and ts_ratio > 0:
                # Typical contango ratio: 0.01-0.10
                strength = min(ts_ratio / 0.10, 1.0)
                raw_score += strength * 66.67
            else:
                raw_score += 33.33  # contango but ratio unknown
        elif ts_state == "flat":
            signals.append("term_structure_flat")
            raw_score += 16.67

    # --- Signal 2: Low panic premium ---
    # Weight: max 0.50 points → normalized to 0-33.33
    if panic_premium is not None:
        # panic_premium = vix_spot - vx1 (typically positive in panic)
        # Low or negative panic premium = fear subsiding = bullish signal
        if panic_premium <= 0:
            signals.append("panic_premium_negative")
            raw_score += 33.33
        elif panic_premium < 1.0:
            signals.append("panic_premium_low")
            raw_score += (1.0 - panic_premium) * 33.33
        elif panic_premium < 3.0:
            signals.append("panic_premium_moderate")
            raw_score += (3.0 - panic_premium) / 3.0 * 16.67

    # --- Signal 3: VIX spot level assessment ---
    if vix_spot is not None:
        if vix_spot < 15:
            signals.append("vix_low")
            raw_score += 10.0
        elif vix_spot < 20:
            signals.append("vix_moderate")
            raw_score += 5.0
        elif vix_spot > 35:
            signals.append("vix_extreme")
            # Extreme VIX can be contrarian bullish for bottom fishing
            raw_score += 15.0

    # Clamp score to 0-100
    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "vix_spot": vix_spot,
            "vx1": vx1,
            "vx2": vx2,
            "term_structure_ratio": ts_ratio,
            "term_structure_state": ts_state or "unknown",
            "panic_premium": panic_premium,
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
