"""
Sector analyzer module.
Analyzes sector rotation and relative strength signals.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "sector_rankings": [],
        "rotation_signal": "none",
        "leading_sectors": [],
        "lagging_sectors": [],
        "breadth": None,
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze sector data and return score, level, signals, and details.

    Args:
        data: Sector data dict. Expected keys:
            - sectors: list[dict] — sector performance data
                Each dict: {name, return_1d, return_5d, return_20d, relative_strength}
            - rotation_signal: str — 'risk_on' | 'risk_off' | 'neutral'
            - breadth: float — market breadth (advance/decline)

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_sector_analysis(data)
    except Exception as e:
        logger.error(f"Sector analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_sector_analysis(data: dict) -> dict:
    """Core sector analysis computation."""
    sectors = data.get("sectors", [])
    rotation = data.get("rotation_signal", "neutral")
    breadth = data.get("breadth")

    signals = []
    raw_score = 0.0

    # --- Sector rotation signal ---
    if rotation == "risk_on":
        signals.append("risk_on_rotation")
        raw_score += 30.0
    elif rotation == "risk_off":
        signals.append("risk_off_rotation")
        # Risk-off can signal bottom approaching
        raw_score += 15.0

    # --- Sector breadth ---
    if breadth is not None:
        if breadth > 0.7:
            signals.append("strong_breadth")
            raw_score += 20.0
        elif breadth > 0.5:
            signals.append("moderate_breadth")
            raw_score += 10.0
        elif breadth < 0.2:
            signals.append("extreme_weak_breadth")
            raw_score += 15.0  # Contrarian signal

    # --- Sector rankings ---
    leading = []
    lagging = []
    if sectors:
        sorted_sectors = sorted(
            sectors,
            key=lambda s: s.get("relative_strength", 0),
            reverse=True,
        )
        leading = [s.get("name", "") for s in sorted_sectors[:3]]
        lagging = [s.get("name", "") for s in sorted_sectors[-3:]]

        # Check for defensive leadership (signals risk-off but potential bottom)
        defensive = {"Utilities", "Consumer Staples", "Healthcare"}
        if leading and any(s in defensive for s in leading):
            signals.append("defensive_leadership")
            raw_score += 10.0

        # Check for broad-based selling
        negative_count = sum(
            1 for s in sectors if s.get("return_1d", 0) < 0
        )
        if negative_count > len(sectors) * 0.8:
            signals.append("broad_based_selling")
            raw_score += 15.0

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "sector_rankings": [s.get("name", "") for s in sectors] if sectors else [],
            "rotation_signal": rotation,
            "leading_sectors": leading,
            "lagging_sectors": lagging,
            "breadth": breadth,
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
