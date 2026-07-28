"""
VIX term structure analyzer module.
Analyzes VIX futures term structure and rolling signals.
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
        "rolling_signal": False,
        "contango_strength": None,
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze VIX term structure data and return score, level, signals, and details.

    Args:
        data: VIX term structure data dict. Expected keys:
            - vix_spot: float — VIX spot
            - vx1: float — VIX 1-month futures
            - vx2: float — VIX 2-month futures
            - term_structure_ratio: float — (vx2/vx1) - 1
            - historical_ratios: list[float] — recent ratio history
            - rolling_signal: bool — rolling event detected

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_vix_term_analysis(data)
    except Exception as e:
        logger.error(f"VIX term structure analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_vix_term_analysis(data: dict) -> dict:
    """Core VIX term structure analysis computation."""
    vix_spot = data.get("vix_spot")
    vx1 = data.get("vx1")
    vx2 = data.get("vx2")
    ts_ratio = data.get("term_structure_ratio")
    historical = data.get("historical_ratios", [])
    rolling = data.get("rolling_signal", False)

    signals = []
    raw_score = 0.0

    # --- Term structure state ---
    ts_state = "unknown"
    contango_strength = None

    if vx1 is not None and vx2 is not None and vx1 > 0:
        computed_ratio = (vx2 / vx1) - 1.0
        ts_ratio = ts_ratio if ts_ratio is not None else computed_ratio

        if ts_ratio > 0.02:
            ts_state = "contango"
            contango_strength = min(ts_ratio / 0.10, 1.0)
            signals.append("contango")
            raw_score += contango_strength * 40.0
        elif ts_ratio < -0.02:
            ts_state = "backwardation"
            signals.append("backwardation")
            # Backwardation = panic, can be contrarian bullish at extremes
            if ts_ratio < -0.10:
                signals.append("extreme_backwardation")
                raw_score += 30.0
            else:
                raw_score += 10.0
        else:
            ts_state = "flat"
            signals.append("flat_term_structure")
            raw_score += 15.0

    # --- Spot vs futures spread ---
    if vix_spot is not None and vx1 is not None:
        spot_futures_spread = vix_spot - vx1
        if spot_futures_spread > 2.0:
            signals.append("spot_premium")
            raw_score += 15.0
        elif spot_futures_spread < -2.0:
            signals.append("futures_premium")
            raw_score += 20.0

    # --- Rolling signal ---
    if rolling:
        signals.append("rolling_event")
        raw_score += 20.0

    # --- Historical context ---
    if historical and ts_ratio is not None:
        import numpy as np
        hist_arr = np.array(historical)
        current_pct = np.sum(hist_arr < ts_ratio) / len(hist_arr) * 100
        if current_pct > 90:
            signals.append("term_structure_extreme_high")
            raw_score += 15.0

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
            "term_structure_state": ts_state,
            "rolling_signal": rolling,
            "contango_strength": round(contango_strength, 4) if contango_strength else None,
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
