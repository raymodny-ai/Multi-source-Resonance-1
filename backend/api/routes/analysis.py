"""
Analysis results API routes.
Provides endpoints for querying the latest analysis results from each quant analyzer.
"""

import logging

from fastapi import APIRouter

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/gex")
async def analysis_gex():
    """Latest GEX analysis results — snapshot with strikes summary."""
    async with get_db() as db:
        # Latest snapshot
        snap_cursor = await db.execute("""
            SELECT * FROM v_latest_gex_snapshot WHERE symbol = 'SPX'
        """)
        snap_row = await snap_cursor.fetchone()
        snapshot = dict(snap_row) if snap_row else None

        # Strike summary stats
        strike_stats = None
        if snapshot:
            stats_cursor = await db.execute("""
                SELECT COUNT(*) AS strike_count,
                       MIN(strike) AS min_strike,
                       MAX(strike) AS max_strike,
                       SUM(call_gex) AS total_call_gex,
                       SUM(put_gex) AS total_put_gex
                FROM gex_strikes
                WHERE snapshot_id = ?
            """, (snapshot["id"],))
            stats_row = await stats_cursor.fetchone()
            strike_stats = dict(stats_row) if stats_row else None

    return {
        "snapshot": snapshot,
        "strike_stats": strike_stats,
    }


@router.get("/vix")
async def analysis_vix():
    """Latest VIX analysis results."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM vix_analysis
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No VIX analysis data available"}
        data = dict(row)

    return {
        "timestamp": data.get("timestamp"),
        "vix_spot": data.get("vix_spot"),
        "vx1": data.get("vx1"),
        "vx2": data.get("vx2"),
        "term_structure_ratio": data.get("term_structure_ratio"),
        "term_structure_state": data.get("term_structure_state"),
        "panic_premium": data.get("panic_premium"),
        "analysis": {
            "contango": data.get("term_structure_state") == "contango",
            "backwardation": data.get("term_structure_state") == "backwardation",
            "high_panic": (data.get("panic_premium") or 0) > 5,
        },
    }


@router.get("/crypto")
async def analysis_crypto():
    """Latest crypto derivatives analysis results."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM crypto_derivatives
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No crypto analysis data available"}
        data = dict(row)

    return {
        "timestamp": data.get("timestamp"),
        "btc_funding_rate": data.get("btc_funding_rate"),
        "btc_oi": data.get("btc_oi"),
        "oi_change_1h": data.get("oi_change_1h"),
        "liquidation_spike": data.get("liquidation_spike"),
        "cryptoquant_elr": data.get("cryptoquant_elr"),
        "funding_anomaly": data.get("funding_anomaly"),
        "oi_crash": data.get("oi_crash"),
        "leverage_cleanup": data.get("leverage_cleanup"),
        "analysis": {
            "leverage_cleanup_active": bool(data.get("leverage_cleanup")),
            "funding_negative": (data.get("btc_funding_rate") or 0) < 0,
            "oi_declining": (data.get("oi_change_1h") or 0) < 0,
        },
    }


@router.get("/darkpool")
async def analysis_darkpool():
    """Latest darkpool analysis results."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM dark_pool_metrics
            ORDER BY date DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No darkpool analysis data available"}
        data = dict(row)

    return {
        "date": data.get("date"),
        "dix_value": data.get("dix_value"),
        "v_net": data.get("v_net"),
        "ema_fast_5": data.get("ema_fast_5"),
        "ema_slow_20": data.get("ema_slow_20"),
        "aggregated_signal": data.get("aggregated_signal"),
        "zero_cross_signal": data.get("zero_cross_signal"),
        "momentum_reversal_signal": data.get("momentum_reversal_signal"),
        "analysis": {
            "dix_bullish": (data.get("dix_value") or 0) > 50,
            "ema_bullish_cross": data.get("zero_cross_signal") == "bullish_cross",
            "momentum_reversing": data.get("momentum_reversal_signal") is not None,
        },
    }


@router.get("/scoring")
async def analysis_scoring():
    """Latest comprehensive scoring results — all dimensions combined."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {
                "message": "No scoring data available yet",
                "total_score": 0.0,
                "alert_level": "NONE",
            }
        data = dict(row)

    return {
        "trigger_time": data.get("trigger_time"),
        "total_score": data.get("total_score"),
        "gex_score": data.get("gex_score"),
        "vix_score": data.get("vix_score"),
        "crypto_score": data.get("crypto_score"),
        "darkpool_score": data.get("darkpool_score"),
        "alert_level": data.get("alert_level"),
        "hawkes_branching_ratio": data.get("hawkes_branching_ratio"),
        "acknowledged": data.get("acknowledged"),
        "max_score": 100.0,
        "level_thresholds": {
            "LEVEL_1": 25.0,
            "LEVEL_2": 50.0,
            "LEVEL_3": 75.0,
        },
    }
