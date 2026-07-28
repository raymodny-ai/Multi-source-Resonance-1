"""
Dark pool / DIX metrics API routes.
"""

import logging

from fastapi import APIRouter, Query

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/darkpool", tags=["Darkpool"])


@router.get("/latest")
async def darkpool_latest():
    """Latest dark pool metrics."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM dark_pool_metrics
            ORDER BY date DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No darkpool data available yet"}
        return dict(row)


@router.get("/flow")
async def darkpool_flow(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
):
    """Dark pool flow data — DIX, V_Net, EMA signals."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT date, dix_value, v_net, ema_fast_5, ema_slow_20,
                   aggregated_signal, zero_cross_signal, momentum_reversal_signal
            FROM v_daily_darkpool
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/history")
async def darkpool_history(
    days: int = Query(90, ge=1, le=365, description="Number of days of history"),
):
    """Full dark pool metrics history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM dark_pool_metrics
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
