"""
Signal & alerts API routes.
Provides endpoints for resonance signal queries and acknowledgement.
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from backend.database import get_db
from backend.quant.signal_outcomes import SignalOutcomeTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["Signals"])


@router.get("/latest")
async def signals_latest():
    """Latest resonance signal alert."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No signals recorded yet"}
        return dict(row)


@router.get("/current")
async def signals_current():
    """Current active signals (unacknowledged alerts)."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            WHERE acknowledged = 0
            ORDER BY trigger_time DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/history")
async def signals_history(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
):
    """Signal history with pagination."""
    async with get_db() as db:
        # Total count
        count_cursor = await db.execute("SELECT COUNT(*) AS cnt FROM signal_alerts")
        count_row = await count_cursor.fetchone()
        total = count_row["cnt"] if count_row else 0

        # Paginated results
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "offset": offset,
            "limit": limit,
        }


@router.get("/scores")
async def signals_scores(
    days: int = Query(90, ge=1, le=365, description="Number of days"),
):
    """Scoring history — dimension breakdown over time."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT trigger_time, total_score, gex_score, vix_score,
                   crypto_score, darkpool_score, alert_level,
                   hawkes_branching_ratio
            FROM signal_alerts
            WHERE trigger_time >= datetime('now', '-' || ? || ' days')
            ORDER BY trigger_time ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.post("/acknowledge/{signal_id}")
async def acknowledge_signal(signal_id: int, request: Request):
    """Acknowledge a signal alert (requires JWT)."""
    async with get_db() as db:
        # Check signal exists
        cursor = await db.execute(
            "SELECT id FROM signal_alerts WHERE id = ?", (signal_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

        # Update acknowledged flag
        await db.execute(
            "UPDATE signal_alerts SET acknowledged = 1 WHERE id = ?",
            (signal_id,),
        )

    return {"ok": True, "message": f"Signal {signal_id} acknowledged"}


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    level: str = Query(None, description="Filter by alert level"),
):
    """List signal alerts with optional level filter."""
    async with get_db() as db:
        if level:
            cursor = await db.execute("""
                SELECT * FROM signal_alerts
                WHERE alert_level = ?
                ORDER BY trigger_time DESC
                LIMIT ?
            """, (level.upper(), limit))
        else:
            cursor = await db.execute("""
                SELECT * FROM signal_alerts
                ORDER BY trigger_time DESC
                LIMIT ?
            """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert (alias endpoint, requires JWT)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM signal_alerts WHERE id = ?", (alert_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        await db.execute(
            "UPDATE signal_alerts SET acknowledged = 1 WHERE id = ?",
            (alert_id,),
        )

    return {"ok": True, "message": f"Alert {alert_id} acknowledged"}


@router.get("/outcomes")
async def signal_outcomes(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
):
    """Signal outcome statistics: false positive rate and hit rate over the last N days."""
    tracker = SignalOutcomeTracker()
    async with get_db() as db:
        fpr = await tracker.get_false_positive_rate(db, days=days)
        perf = await tracker.get_signal_performance(db, days=days)
    return {
        "lookback_days": days,
        "false_positive_rate": fpr,
        **perf,
    }


@router.get("/performance")
async def signal_performance(
    days: int = Query(90, ge=1, le=365, description="Lookback window in days"),
):
    """Detailed signal performance: hit rate, average return, max drawdown."""
    tracker = SignalOutcomeTracker()
    async with get_db() as db:
        perf = await tracker.get_signal_performance(db, days=days)
    return {
        "lookback_days": days,
        **perf,
    }
