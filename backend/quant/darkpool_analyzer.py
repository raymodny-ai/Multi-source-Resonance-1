"""
Darkpool analyzer module.
Analyzes dark pool trading data including DIX, short ratios, and institutional flow.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "dix_value": None,
        "v_net": None,
        "short_ratio": None,
        "ema_fast_5": None,
        "ema_slow_20": None,
        "zero_cross_signal": None,
        "aggregated_signal": False,
        "flow_direction": "neutral",
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze dark pool data and return score, level, signals, and details.

    Args:
        data: Dark pool data dict from darkpool/SqueezeMetrics fetcher. Expected keys:
            - dix_value: float — Dark Index value
            - chartexchange_short_ratio: float — short ratio
            - stockgrid_20d_slope: float — 20-day price slope
            - stockgrid_60d_slope: float — 60-day price slope
            - stockgrid_divergence: bool — price/volume divergence
            - dbmf_ma5_recovery: bool — MA5 recovery flag
            - v_net: float — net short volume
            - ema_fast_5: float — EMA 5-day
            - ema_slow_20: float — EMA 20-day
            - zero_cross_signal: str — 'bullish_cross' | 'bearish_cross'
            - momentum_reversal_signal: str
            - aggregated_signal: bool

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_darkpool_analysis(data)
    except Exception as e:
        logger.error(f"Darkpool analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_darkpool_analysis(data: dict) -> dict:
    """Core darkpool analysis computation."""
    dix = data.get("dix_value")
    short_ratio = data.get("chartexchange_short_ratio")
    v_net = data.get("v_net")
    ema5 = data.get("ema_fast_5")
    ema20 = data.get("ema_slow_20")
    zero_cross = data.get("zero_cross_signal")
    momentum_rev = data.get("momentum_reversal_signal")
    agg_signal = data.get("aggregated_signal", False)
    divergence = data.get("stockgrid_divergence", False)
    ma5_recovery = data.get("dbmf_ma5_recovery", False)

    signals = []
    raw_score = 0.0

    # --- Signal 1: DIX bullish (institutional accumulation) ---
    # Weight: max 1.00 points → normalized to 0-50.0 (of 2.0 total weight)
    if dix is not None:
        # DIX > 45 = institutional buying (dark pool accumulation)
        # DIX > 50 = strong accumulation
        if dix > 50:
            signals.append("dix_strong_bullish")
            raw_score += 50.0
        elif dix > 45:
            signals.append("dix_bullish")
            raw_score += 30.0
        elif dix > 40:
            signals.append("dix_neutral")
            raw_score += 10.0

    # --- Signal 2: Short ratio extreme ---
    # Weight: max 0.50 points → normalized to 0-25.0
    if short_ratio is not None:
        if short_ratio > 5.0:
            signals.append("short_ratio_extreme")
            raw_score += 25.0
        elif short_ratio > 3.0:
            signals.append("short_ratio_high")
            raw_score += 15.0

    # --- Signal 3: EMA momentum reversal ---
    # Weight: max 0.50 points → normalized to 0-25.0
    # AUDIT follow-up (2026-08-02, Owner decision #1): a bullish cross where
    # BOTH EMAs are still deeply negative is NOT a new bullish signal — it's
    # just short-covering (空头动能减弱). It should not score anywhere near
    # a genuine reversal. Require at least one EMA >= 0 for full bullish
    # weight; otherwise downgrade to a small short-cover signal.
    if zero_cross == "bullish_cross":
        if ema5 is not None and ema20 is not None and (ema5 >= 0 or ema20 >= 0):
            signals.append("ema_bullish_cross")
            raw_score += 25.0
        else:
            # still-negative crossover = short covering, minor
            signals.append("ema_short_cover")
            raw_score += 8.0
    elif momentum_rev:
        signals.append("momentum_reversal")
        raw_score += 20.0

    # --- Signal 4: Aggregated signal ---
    if agg_signal:
        signals.append("aggregated_bullish")
        raw_score += 15.0

    # --- Signal 5: MA5 recovery ---
    if ma5_recovery:
        signals.append("ma5_recovery")
        raw_score += 10.0

    # --- Signal 6: Stockgrid divergence (price down but volume supports reversal) ---
    if divergence:
        signals.append("price_volume_divergence")
        raw_score += 10.0

    # Determine flow direction
    flow_direction = "neutral"
    if v_net is not None:
        if v_net > 0:
            flow_direction = "net_long"
        elif v_net < 0:
            flow_direction = "net_short"

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "dix_value": dix,
            "v_net": v_net,
            "short_ratio": short_ratio,
            "ema_fast_5": ema5,
            "ema_slow_20": ema20,
            "zero_cross_signal": zero_cross,
            "aggregated_signal": agg_signal,
            "flow_direction": flow_direction,
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
