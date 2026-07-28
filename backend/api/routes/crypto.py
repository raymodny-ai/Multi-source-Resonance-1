"""
Crypto derivatives data API routes.
"""

import logging

from fastapi import APIRouter, Query

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crypto", tags=["Crypto"])


@router.get("/latest")
async def crypto_latest():
    """Latest crypto derivatives signal."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM crypto_derivatives
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            return {"message": "No crypto data available yet"}
        return dict(row)


@router.get("/history")
async def crypto_history(
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
):
    """Crypto derivatives history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM crypto_derivatives
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
