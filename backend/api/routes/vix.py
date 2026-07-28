"""
VIX term structure data API routes.
"""

import logging

from fastapi import APIRouter, Query

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vix", tags=["VIX"])


@router.get("/latest")
async def vix_latest():
    """Latest VIX term structure snapshot."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM vix_analysis
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No VIX data available yet"}
        return dict(row)


@router.get("/term-structure")
async def vix_term_structure():
    """VIX term structure — spot, VX1, VX2, contango/backwardation state."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT timestamp, vix_spot, vx1, vx2,
                   term_structure_ratio, term_structure_state, panic_premium
            FROM vix_analysis
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No VIX term structure data available"}
        data = dict(row)
        return {
            "vix_spot": data.get("vix_spot"),
            "vx1": data.get("vx1"),
            "vx2": data.get("vx2"),
            "term_structure_ratio": data.get("term_structure_ratio"),
            "term_structure_state": data.get("term_structure_state"),
            "panic_premium": data.get("panic_premium"),
            "timestamp": data.get("timestamp"),
        }


@router.get("/history")
async def vix_history(
    days: int = Query(90, ge=1, le=365, description="Number of days of history"),
):
    """VIX term structure history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM vix_analysis
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/term-structure-history")
async def vix_term_structure_history(
    days: int = Query(365, ge=1, le=1825, description="Days of history (max ~5y)"),
):
    """VIX term structure daily history (FRED VIXCLS + VXVCLS, ~2 years).

    Returns one row per trading day with VIX spot, 3M VIX proxy (VXVCLS),
    term structure ratio/state, panic premium, and vol regime.
    """
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT date, vix_spot, vx_3m_proxy, term_structure_ratio,
                   term_structure_state, panic_premium, regime
            FROM vix_term_structure
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
