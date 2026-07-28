"""
Flow analyzer module.
Analyzes capital flow data to determine main capital direction.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "flow_direction": "neutral",
        "flow_strength": 0.0,
        "net_flow": None,
        "flow_trend": "unknown",
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze flow data and return score, level, signals, and details.

    Args:
        data: Flow data dict. Expected keys:
            - net_flow: float — net capital flow
            - flow_ma5: float — 5-day moving average of flow
            - flow_ma20: float — 20-day moving average of flow
            - flow_direction: str — 'inflow' | 'outflow' | 'neutral'
            - volume_ratio: float — relative volume ratio

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_flow_analysis(data)
    except Exception as e:
        logger.error(f"Flow analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_flow_analysis(data: dict) -> dict:
    """Core flow analysis computation."""
    net_flow = data.get("net_flow")
    flow_ma5 = data.get("flow_ma5")
    flow_ma20 = data.get("flow_ma20")
    volume_ratio = data.get("volume_ratio", 1.0)

    signals = []
    raw_score = 0.0

    # --- Signal 1: Net flow direction ---
    if net_flow is not None:
        if net_flow > 0:
            signals.append("net_inflow")
            raw_score += 30.0
        elif net_flow < -1e6:
            signals.append("significant_outflow")
            # Outflow can be contrarian for bottom fishing
            raw_score += 15.0

    # --- Signal 2: Flow MA crossover ---
    if flow_ma5 is not None and flow_ma20 is not None:
        if flow_ma5 > flow_ma20:
            signals.append("flow_ma_bullish_cross")
            raw_score += 25.0
        elif flow_ma5 < flow_ma20:
            signals.append("flow_ma_bearish_cross")

    # --- Signal 3: Volume ratio ---
    if volume_ratio and volume_ratio > 1.5:
        signals.append("high_volume")
        raw_score += 15.0

    # Determine flow direction and strength
    flow_direction = "neutral"
    if net_flow is not None:
        if net_flow > 0:
            flow_direction = "inflow"
        elif net_flow < 0:
            flow_direction = "outflow"

    flow_strength = min(abs(net_flow or 0) / 1e9, 1.0) * 100
    flow_trend = "stable"
    if flow_ma5 and flow_ma20:
        if flow_ma5 > flow_ma20 * 1.1:
            flow_trend = "accelerating"
        elif flow_ma5 < flow_ma20 * 0.9:
            flow_trend = "decelerating"

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "flow_direction": flow_direction,
            "flow_strength": round(flow_strength, 2),
            "net_flow": net_flow,
            "flow_trend": flow_trend,
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
