"""
GEX (Gamma Exposure) analyzer module.
Analyzes GEXMetrix data to compute key indicators and generate trading signals.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default values for mock/empty data
_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "net_gex": 0.0,
        "call_wall": None,
        "put_wall": None,
        "zero_gamma_level": None,
        "spot_price": None,
        "call_gex_total": 0.0,
        "put_gex_total": 0.0,
        "total_gamma": 0.0,
        "gex_regime": "unknown",
    },
}


def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from dict, returning default if None or missing."""
    val = data.get(key, default)
    return val if val is not None else default


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze GEX data and return score, level, signals, and details.

    Args:
        data: GEX data dict from GEXMetrixFetcher output. Expected keys:
            - net_gex: float — net gamma exposure
            - call_gex: float — total call GEX
            - put_gex: float — total put GEX (negative)
            - call_wall: float — call wall strike price
            - put_wall: float — put wall strike price
            - zero_gamma_level: float — zero gamma price level
            - spot_price: float — underlying spot price
            - total_gamma: float — total absolute gamma
            - strikes: list[dict] — per-strike GEX data (optional)

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        return _default_result()

    try:
        # GEXMetrixFetcher.fetch() returns {"snapshots": [...], "strikes": [...]}.
        # Analyzers expect a flat snapshot dict (net_gex, call_wall, ...). Adapt:
        # if the payload carries a snapshots array, analyze the latest snapshot
        # (first element) so the GEX dimension scores real data instead of 0.
        if isinstance(data, dict) and data.get("snapshots"):
            snaps = data["snapshots"]
            if isinstance(snaps, list) and snaps:
                data = snaps[-1]  # latest snapshot (ASC appended order if present)

        return _compute_gex_analysis(data)
    except Exception as e:
        logger.error(f"GEX analysis failed: {e}", exc_info=True)
        return _default_result()


def _default_result() -> dict:
    """Return a deep copy of the default result."""
    import copy
    return copy.deepcopy(_DEFAULT_RESULT)


def _compute_gex_analysis(data: dict) -> dict:
    """Core GEX analysis computation."""
    net_gex = _safe_get(data, "net_gex", 0.0) or 0.0
    call_gex_total = _safe_get(data, "call_gex", 0.0) or 0.0
    put_gex_total = _safe_get(data, "put_gex", 0.0) or 0.0
    call_wall = _safe_get(data, "call_wall")
    put_wall = _safe_get(data, "put_wall")
    zero_gamma = _safe_get(data, "zero_gamma_level")
    spot_price = _safe_get(data, "spot_price")
    total_gamma = _safe_get(data, "total_gamma", 0.0) or 0.0

    signals = []
    raw_score = 0.0

    # Determine GEX regime
    gex_regime = "positive" if net_gex > 0 else "negative"

    # --- Signal 1: Net GEX positive (dealer long gamma → mean-reverting market) ---
    # Weight: max 1.50 points → normalized to 0-37.5 in 0-100 scale (weight 2.5 total)
    if net_gex > 0:
        signals.append("net_gex_positive")
        # Score based on magnitude relative to total gamma
        if total_gamma > 0:
            gex_ratio = net_gex / total_gamma
            # gex_ratio typically in [-1, 1], positive is bullish for signal
            raw_score += min(gex_ratio, 1.0) * 37.5
        else:
            raw_score += 18.75  # moderate score if total_gamma unknown

    # --- Signal 2: Spot below zero gamma level (in positive gamma territory) ---
    # Weight: max 0.50 points → normalized to 0-12.5
    if zero_gamma and spot_price:
        if spot_price < zero_gamma:
            signals.append("spot_below_zero_gamma")
            distance_pct = (zero_gamma - spot_price) / spot_price * 100
            # Closer to zero gamma = stronger signal, but being below is already good
            proximity_score = max(0, 1.0 - distance_pct / 10.0)
            raw_score += proximity_score * 12.5

    # --- Signal 3: Proximity to call wall ---
    # Weight: max 0.50 points → normalized to 0-12.5
    if call_wall and spot_price and spot_price > 0:
        distance_to_call_wall = abs(call_wall - spot_price) / spot_price
        if distance_to_call_wall < 0.05:  # within 5%
            signals.append("near_call_wall")
            proximity = 1.0 - (distance_to_call_wall / 0.05)
            raw_score += proximity * 12.5

    # --- Signal 4: Put wall support ---
    if put_wall and spot_price and spot_price > 0:
        distance_to_put_wall = abs(spot_price - put_wall) / spot_price
        if distance_to_put_wall < 0.03:
            signals.append("near_put_wall_support")
            raw_score += 5.0  # small bonus

    # --- Signal 5: GEX flip zone detection ---
    flip_zone_lower = _safe_get(data, "flip_zone_lower")
    flip_zone_upper = _safe_get(data, "flip_zone_upper")
    if flip_zone_lower and flip_zone_upper and spot_price:
        if flip_zone_lower <= spot_price <= flip_zone_upper:
            signals.append("in_flip_zone")
            raw_score += 12.5  # significant bonus for being in flip zone

    # Clamp score to 0-100
    final_score = max(0.0, min(100.0, raw_score))

    # Determine level
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "net_gex": net_gex,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "zero_gamma_level": zero_gamma,
            "spot_price": spot_price,
            "call_gex_total": call_gex_total,
            "put_gex_total": put_gex_total,
            "total_gamma": total_gamma,
            "gex_regime": gex_regime,
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
    else:
        return "LEVEL_0"
