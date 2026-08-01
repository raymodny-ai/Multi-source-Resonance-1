"""
Sector rotation API routes.
Exposes real yfinance sector ETF rotation data (per-ETF returns + aggregate
rotation signal). Added 2026-08-02 — was previously always-mock dead data.
"""

import logging

from fastapi import APIRouter, Query

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sector", tags=["Sector"])


@router.get("/latest")
async def sector_latest():
    """Latest sector rotation snapshot (aggregate + per-sector returns)."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM sector_rotation_aggregates
               ORDER BY timestamp DESC LIMIT 1"""
        )
        agg = await cursor.fetchone()
        if not agg:
            return {"message": "No sector rotation data available yet"}

        agg = dict(agg)
        # Attach per-sector returns for the same timestamp
        cursor = await db.execute(
            """SELECT symbol, name, daily_return, weekly_return, monthly_return
               FROM sector_rotation WHERE timestamp = ? ORDER BY symbol""",
            (agg["timestamp"],),
        )
        per_sector = [dict(r) for r in await cursor.fetchall()]

        agg["sector_performance"] = per_sector
        # Expand best/worst etf codes to full names
        best = agg.get("best_sector")
        worst = agg.get("worst_sector")
        names = {s["symbol"]: s["name"] for s in per_sector}
        agg["best_sector"] = {"etf": best, "name": names.get(best)}
        agg["worst_sector"] = {"etf": worst, "name": names.get(worst)}
        return agg


@router.get("/history")
async def sector_history(
    days: int = Query(14, ge=1, le=90, description="Number of days of rotation signal history"),
):
    """Rotation signal trend over the last N days."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT timestamp, rotation_signal, defensive_avg_return,
                      cyclical_avg_return, best_sector, worst_sector
               FROM sector_rotation_aggregates
               WHERE timestamp >= datetime('now', '-' || ? || ' days')
               ORDER BY timestamp ASC""",
            (days,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
