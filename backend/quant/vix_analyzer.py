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
    """Core VIX analysis computation.

    2026-08-02 (方案 A): measure deviation from NORMAL, not normalcy itself.
    The old logic scored contango + negative panic premium — the most COMMON
    state in calm markets — as a near-max bullish signal, structurally pinning
    the score ~100 and stripping it of signal value. Now:
      - deep contango (ratio > 0.10) + settled negative premium = little new
        info → LOW score (market already calm)
      - freshly-recovering contango (0.02-0.10) + premium fading to ~0 = the
        panic-subside transition → HIGH score
      - panic (backwardation + high premium) or extreme VIX = contrarian
        opportunities / transition points, scored moderately-high
    """
    vix_spot = data.get("vix_spot")
    vx1 = data.get("vx1")
    vx2 = data.get("vx2")
    ts_ratio = data.get("term_structure_ratio")
    ts_state = data.get("term_structure_state")
    panic_premium = data.get("panic_premium")

    signals = []
    raw_score = 0.0

    # --- Signal 1: Term-structure transition signal (not level) ---
    # Weight: max 50.0. We score the *recovery* from backwardation, not a
    # settled contango. Deep/steady contango (market already calm) → low.
    if ts_state:
        if ts_state == "contango":
            if ts_ratio is not None:
                if 0.02 < ts_ratio <= 0.05:
                    # Just entered contango — panic-subside turning point
                    signals.append("term_structure_recovery")
                    raw_score += 50.0
                elif 0.05 < ts_ratio <= 0.10:
                    # Moderate contango — recovery in progress
                    signals.append("term_structure_normalizing")
                    raw_score += 30.0
                elif ts_ratio > 0.10:
                    # Deep contango — market already calm, no new signal
                    signals.append("term_structure_deep_contango")
                    raw_score += 10.0
                else:
                    # 0 < ratio <= 0.02 — borderline flat/positive
                    signals.append("term_structure_recovery")
                    raw_score += 50.0
            else:
                # Contango but ratio unknown — mild credit
                signals.append("term_structure_contango")
                raw_score += 20.0
        elif ts_state == "flat":
            signals.append("term_structure_flat")
            raw_score += 20.0
        elif ts_state == "backwardation":
            # Panic → not a bullish signal; 0 points (transition handled below)
            signals.append("term_structure_backwardation")

    # --- Signal 2: Panic premium fading (not merely negative) ---
    # Weight: max 35.0. premium already negative = calm, low info. Premium high
    # and rising = panic, not bullish. The USEFUL signal is premium near zero
    # from above (fear fading) — scored highest.
    if panic_premium is not None:
        if panic_premium <= 0:
            # Already settled/negative — market calm, little new info
            signals.append("panic_premium_settled")
            raw_score += 10.0
        elif panic_premium < 1.0:
            # Near zero from above — fear subsiding (best transition signal)
            signals.append("panic_premium_fading")
            raw_score += 35.0
        elif panic_premium < 3.0:
            # Moderate premium — mild fear, partial recovery
            signals.append("panic_premium_moderate")
            raw_score += 20.0
        else:
            # premium >= 3 — real panic, not a bullish signal
            signals.append("panic_premium_elevated")

    # --- Signal 3: VIX absolute level (kept, re-weighted) ---
    # Weight: max 25.0. Very low / extreme VIX carry the most info; middling
    # levels are common and get little credit.
    if vix_spot is not None:
        if vix_spot < 13:
            signals.append("vix_very_low")
            raw_score += 10.0
        elif vix_spot < 18:
            signals.append("vix_low")
            raw_score += 5.0
        elif vix_spot > 35:
            # Extreme VIX — contrarian bottom-fishing opportunity preserved
            signals.append("vix_extreme_contrarian")
            raw_score += 25.0

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
