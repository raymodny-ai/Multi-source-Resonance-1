"""
GEX (Gamma Exposure) data API routes.
Provides endpoints for GEX snapshots, strikes, history, and BFF dashboard-view.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gex", tags=["GEX"])


@router.get("/symbols")
async def gex_symbols():
    """All available underlying symbols with freshness info."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT symbol,
                   MAX(timestamp) AS latest_timestamp,
                   COUNT(*) AS snapshot_count,
                   CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
            FROM gex_snapshots
            GROUP BY symbol
            ORDER BY symbol
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/summary")
async def gex_summary():
    """Latest GEX snapshot summary for all 6 symbols (one-shot)."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM v_latest_gex_snapshot ORDER BY symbol")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/history")
async def gex_history(
    days: int = Query(90, ge=1, le=365, description="Number of days of history"),
):
    """SqueezeMetrics 90-day GEX history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM gex_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/alpha-history")
async def alpha_history(
    days: int = Query(90, ge=1, le=365),
):
    """Alpha factor history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM alpha_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/{symbol}/latest")
async def gex_latest(symbol: str):
    """Latest GEXMetrix snapshot for a specific symbol."""
    symbol = symbol.upper()
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM gex_snapshots
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (symbol,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No GEX data for symbol '{symbol}'")
        return dict(row)


@router.get("/{symbol}/history")
async def gex_symbol_history(
    symbol: str,
    days: int = Query(3, ge=1, le=30, description="Number of days"),
):
    """GEXMetrix time series for a symbol (short window, max 30 days)."""
    symbol = symbol.upper()
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM gex_snapshots
            WHERE symbol = ?
              AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (symbol, days))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/{symbol}/levels")
async def gex_levels(symbol: str):
    """Key GEX levels: call_wall, put_wall, zero_gamma for a symbol."""
    symbol = symbol.upper()
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT symbol, call_wall, put_wall, zero_gamma_level, spot_price,
                   net_gex, call_gex, put_gex, timestamp
            FROM gex_snapshots
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (symbol,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No GEX levels for symbol '{symbol}'")
        return dict(row)


@router.get("/{symbol}/strikes")
async def gex_strikes(
    symbol: str,
    limit: int = Query(200, ge=1, le=600, description="Max number of strikes"),
):
    """Per-strike real GEX/OI distribution for a symbol."""
    symbol = symbol.upper()
    async with get_db() as db:
        # Get latest snapshot id for this symbol
        snap_cursor = await db.execute("""
            SELECT id, timestamp, spot_price FROM gex_snapshots
            WHERE symbol = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (symbol,))
        snap_row = await snap_cursor.fetchone()
        if not snap_row:
            raise HTTPException(status_code=404, detail=f"No strike data for symbol '{symbol}'")

        snapshot_id = snap_row["id"]
        spot_price = snap_row["spot_price"]
        ts = snap_row["timestamp"]

        strikes_cursor = await db.execute("""
            SELECT strike, call_gex, put_gex, call_oi, put_oi,
                   call_vol, put_vol, net_gex
            FROM gex_strikes
            WHERE snapshot_id = ?
            ORDER BY strike ASC
            LIMIT ?
        """, (snapshot_id, limit))
        strikes_rows = await strikes_cursor.fetchall()

        return {
            "symbol": symbol,
            "timestamp": ts,
            "spot_price": spot_price,
            "strike_count": len(strikes_rows),
            "strikes": [dict(r) for r in strikes_rows],
        }


@router.get("/{symbol}/dashboard-view")
async def gex_dashboard_view(
    symbol: str,
    history_days: int = Query(3, ge=1, le=7, description="GEXMetrix short window"),
    long_days: int = Query(90, ge=30, le=365, description="SqueezeMetrics long window"),
    strikes_limit: int = Query(200, ge=10, le=600, description="ATM strike count"),
):
    """BFF aggregation — single call returns 6 sections for Gamma Dashboard.

    Replaces 6 independent frontend useQuery calls, eliminating waterfall.
    Target response time < 10ms.
    """
    symbol = symbol.upper()
    async with get_db() as db:
        # Section 1: Latest snapshot
        latest_cursor = await db.execute("""
            SELECT * FROM gex_snapshots
            WHERE symbol = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (symbol,))
        latest_row = await latest_cursor.fetchone()
        latest = dict(latest_row) if latest_row else None

        # Section 2: Key levels
        levels = None
        if latest:
            levels = {
                "call_wall": latest.get("call_wall"),
                "put_wall": latest.get("put_wall"),
                "zero_gamma_level": latest.get("zero_gamma_level"),
                "spot_price": latest.get("spot_price"),
                "net_gex": latest.get("net_gex"),
                "call_gex": latest.get("call_gex"),
                "put_gex": latest.get("put_gex"),
            }

        # Section 3: Short history (GEXMetrix, 1-7 days)
        hist_cursor = await db.execute("""
            SELECT symbol, timestamp, net_gex, spot_price, call_gex, put_gex,
                   call_wall, put_wall, zero_gamma_level
            FROM gex_snapshots
            WHERE symbol = ?
              AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (symbol, history_days))
        hist_rows = await hist_cursor.fetchall()
        history = [dict(r) for r in hist_rows]

        # Section 4: Long history (SqueezeMetrics, 30-365 days)
        long_cursor = await db.execute("""
            SELECT * FROM gex_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (long_days,))
        long_rows = await long_cursor.fetchall()
        long_history = [dict(r) for r in long_rows]

        # Section 5: Strikes
        strikes_data = None
        if latest:
            snapshot_id = latest["id"]
            strikes_cursor = await db.execute("""
                SELECT strike, call_gex, put_gex, call_oi, put_oi,
                       call_vol, put_vol, net_gex
                FROM gex_strikes
                WHERE snapshot_id = ?
                ORDER BY ABS(strike - ?) ASC
                LIMIT ?
            """, (snapshot_id, latest.get("spot_price", 0), strikes_limit))
            strikes_rows = await strikes_cursor.fetchall()
            strikes_data = {
                "timestamp": latest.get("timestamp"),
                "spot_price": latest.get("spot_price"),
                "strike_count": len(strikes_rows),
                "strikes": [dict(r) for r in strikes_rows],
            }

        # Section 6: All symbols summary
        sym_cursor = await db.execute("""
            SELECT symbol,
                   MAX(timestamp) AS latest_timestamp,
                   COUNT(*) AS snapshot_count,
                   CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
            FROM gex_snapshots
            GROUP BY symbol
            ORDER BY symbol
        """)
        sym_rows = await sym_cursor.fetchall()
        symbols = [dict(r) for r in sym_rows]

    return {
        "symbol": symbol,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "latest": latest,
        "levels": levels,
        "history": history,
        "long_history": long_history,
        "strikes": strikes_data,
        "symbols": symbols,
    }
