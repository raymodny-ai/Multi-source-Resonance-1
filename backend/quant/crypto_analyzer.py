"""
Cryptocurrency analyzer module.
Analyzes crypto market data (BTC/ETH) including funding rates, OI changes,
and leverage cleanup signals.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_RESULT = {
    "score": 0.0,
    "level": "LEVEL_0",
    "signals": [],
    "details": {
        "btc_funding_rate": None,
        "btc_oi": None,
        "oi_change_1h": None,
        "liquidation_spike": False,
        "leverage_cleanup": False,
        "funding_anomaly": False,
        "oi_crash": False,
        "cryptoquant_elr": None,
        "sentiment": "neutral",
    },
}


async def analyze(data: Optional[dict] = None) -> dict:
    """Analyze crypto derivatives data and return score, level, signals, and details.

    Args:
        data: Crypto data dict from CryptoFetcher. Expected keys:
            - btc_funding_rate: float — BTC perpetual funding rate
            - btc_oi: float — BTC open interest
            - oi_change_1h: float — 1h OI change rate
            - liquidation_spike: bool — liquidation spike flag
            - leverage_cleanup: bool — leverage cleanup signal
            - funding_anomaly: bool — funding anomaly flag
            - oi_crash: bool — OI crash flag
            - cryptoquant_elr: float — Estimated Leverage Ratio

    Returns:
        dict with keys: score (0-100), level, signals (list), details (dict)
    """
    if not data:
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    try:
        return _compute_crypto_analysis(data)
    except Exception as e:
        logger.error(f"Crypto analysis failed: {e}", exc_info=True)
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)


def _compute_crypto_analysis(data: dict) -> dict:
    """Core crypto analysis computation."""
    funding_rate = data.get("btc_funding_rate")
    btc_oi = data.get("btc_oi")
    oi_change = data.get("oi_change_1h")
    liq_spike = data.get("liquidation_spike", False)
    lev_cleanup = data.get("leverage_cleanup", False)
    funding_anomaly = data.get("funding_anomaly", False)
    oi_crash = data.get("oi_crash", False)
    elr = data.get("cryptoquant_elr")
    # CoinGecko spot-price enrichment (2026-08-01)
    btc_change = data.get("btc_24h_change")
    eth_change = data.get("eth_24h_change")
    btc_price = data.get("btc_price")

    signals = []
    raw_score = 0.0

    # --- Signal 1: Leverage cleanup (key bottom-fishing signal) ---
    # Weight: max 1.00 points → normalized to 0-50.0 (of 2.0 total weight)
    if lev_cleanup:
        signals.append("leverage_cleanup")
        raw_score += 50.0

    # --- Signal 2: Funding rate anomaly ---
    # Weight: max 0.50 points → normalized to 0-25.0
    if funding_rate is not None:
        # Negative funding = shorts paying longs = bearish sentiment exhausted
        if funding_rate < -0.001:
            signals.append("funding_negative_extreme")
            raw_score += 25.0
        elif funding_rate < 0:
            signals.append("funding_negative")
            raw_score += 15.0
        elif funding_anomaly:
            signals.append("funding_anomaly")
            raw_score += 20.0

    # --- Signal 3: OI crash ---
    # Weight: max 0.50 points → normalized to 0-25.0
    if oi_crash:
        signals.append("oi_crash")
        raw_score += 25.0
    elif oi_change is not None and oi_change < -0.10:
        # >10% OI drop in 1 hour
        signals.append("oi_sharp_decline")
        severity = min(abs(oi_change) / 0.30, 1.0)
        raw_score += severity * 20.0

    # --- Signal 4: Liquidation spike ---
    if liq_spike:
        signals.append("liquidation_spike")
        raw_score += 10.0

    # --- Signal 5: ELR (Estimated Leverage Ratio) assessment ---
    if elr is not None:
        if elr < 1.5:
            signals.append("low_leverage")
            raw_score += 10.0
        elif elr > 3.0:
            signals.append("high_leverage_risk")
            # High leverage = potential for future cleanup, not immediate signal

    # --- Signal 6: CoinGecko spot-price momentum (2026-08-01) ---
    # Uses the stronger of |BTC 24h%| / |ETH 24h%| so a sharp move in either
    # flags crypto risk even when derivatives (funding/OI) are quiet.
    # max 20.0 points
    spot_move = None
    if btc_change is not None or eth_change is not None:
        abs_btc = abs(btc_change) if btc_change is not None else 0.0
        abs_eth = abs(eth_change) if eth_change is not None else 0.0
        if abs_btc >= abs_eth:
            spot_move = btc_change
        else:
            spot_move = eth_change

    if spot_move is not None:
        if spot_move <= -8.0:
            signals.append("spot_crash")
            raw_score += 20.0
        elif spot_move <= -4.0:
            signals.append("spot_sharp_drop")
            raw_score += 15.0
        elif spot_move >= 8.0:
            signals.append("spot_parabolic")
            raw_score += 20.0
        elif spot_move >= 4.0:
            signals.append("spot_strong_rally")
            raw_score += 12.0

    # Determine sentiment
    sentiment = "neutral"
    if raw_score >= 50:
        sentiment = "extreme_fear_cleanup"
    elif raw_score >= 25:
        sentiment = "fear"
    elif funding_rate and funding_rate > 0.01:
        sentiment = "euphoria"
    elif spot_move is not None and spot_move >= 4.0:
        sentiment = "euphoria"

    final_score = max(0.0, min(100.0, raw_score))
    level = _score_to_level(final_score)

    return {
        "score": round(final_score, 2),
        "level": level,
        "signals": signals,
        "details": {
            "btc_funding_rate": funding_rate,
            "btc_oi": btc_oi,
            "oi_change_1h": oi_change,
            "liquidation_spike": liq_spike,
            "leverage_cleanup": lev_cleanup,
            "funding_anomaly": funding_anomaly,
            "oi_crash": oi_crash,
            "cryptoquant_elr": elr,
            "sentiment": sentiment,
            "btc_price": btc_price,
            "btc_24h_change": btc_change,
            "eth_24h_change": eth_change,
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
