"""
Macro analyzer module.
Analyzes macroeconomic indicators and risk event assessments.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "risk_level": "normal",
        "key_indicators": {},
        "upcoming_events": [],
        "macro_stance": "neutral",
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze macroeconomic data and return score, level, signals, and details.

    Args:
        data: Macro data dict. Expected keys:
            - fed_funds_rate: float — Federal funds rate
            - treasury_yields: dict — {2y, 10y, 30y} yields
            - yield_curve_inverted: bool — 2s10s inversion flag
            - unemployment_rate: float — latest unemployment
            - cpi_yoy: float — CPI year-over-year
            - pmi: float — Purchasing Managers Index
            - risk_events: list[dict] — upcoming risk events
            - dollar_index: float — DXY

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_macro_analysis(data)
    except Exception as e:
        logger.error(f"Macro analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_macro_analysis(data: dict) -> dict:
    """Core macro analysis computation."""
    yields = data.get("treasury_yields", {})
    curve_inverted = data.get("yield_curve_inverted", False)
    unemployment = data.get("unemployment_rate")
    cpi = data.get("cpi_yoy")
    pmi = data.get("pmi")
    risk_events = data.get("risk_events", [])
    dxy = data.get("dollar_index")

    signals = []
    raw_score = 0.0

    # --- Yield curve inversion ---
    if curve_inverted:
        signals.append("yield_curve_inverted")
        raw_score += 30.0  # Recession signal
        # Un-inversion after prolonged inversion is often the trigger
        if yields.get("10y") and yields.get("2y"):
            spread = yields["10y"] - yields["2y"]
            if -0.1 < spread < 0:
                signals.append("yield_curve_uninverting")
                raw_score += 20.0

    # --- PMI ---
    if pmi is not None:
        if pmi < 47:
            signals.append("pmi_deep_contraction")
            raw_score += 25.0
        elif pmi < 50:
            signals.append("pmi_contraction")
            raw_score += 15.0
        elif pmi > 55:
            signals.append("pmi_expansion")
            raw_score += 5.0

    # --- Unemployment ---
    if unemployment is not None:
        if unemployment > 6.0:
            signals.append("high_unemployment")
            raw_score += 20.0
        elif unemployment > 5.0:
            signals.append("rising_unemployment")
            raw_score += 10.0

    # --- CPI ---
    if cpi is not None:
        if cpi > 5.0:
            signals.append("high_inflation")
            raw_score += 15.0
        elif cpi < 1.0:
            signals.append("deflation_risk")
            raw_score += 20.0  # Deflation = dovish pivot expected

    # --- Risk events ---
    upcoming = []
    for event in risk_events[:5]:
        upcoming.append({
            "name": event.get("name", "Unknown"),
            "date": event.get("date", ""),
            "impact": event.get("impact", "medium"),
        })
        if event.get("impact") == "high":
            signals.append("high_impact_event")
            raw_score += 10.0

    # --- Dollar strength ---
    if dxy is not None:
        if dxy > 110:
            signals.append("strong_dollar")
            raw_score += 10.0
        elif dxy < 95:
            signals.append("weak_dollar")
            raw_score += 5.0

    # Determine macro stance
    macro_stance = "neutral"
    if raw_score >= 50:
        macro_stance = "risk_off"
    elif raw_score >= 25:
        macro_stance = "cautious"
    elif raw_score < 10:
        macro_stance = "risk_on"

    risk_level = "normal"
    if raw_score >= 60:
        risk_level = "high"
    elif raw_score >= 30:
        risk_level = "elevated"

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "risk_level": risk_level,
            "key_indicators": {
                "treasury_yields": yields,
                "unemployment": unemployment,
                "cpi": cpi,
                "pmi": pmi,
                "dollar_index": dxy,
            },
            "upcoming_events": upcoming,
            "macro_stance": macro_stance,
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
