"""Options chain + Greeks API endpoints (yfinance + py_vollib Black-Scholes local calc)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db

router = APIRouter(prefix="/api/options", tags=["options"])


class OptionsGreeksSnapshot(BaseModel):
    id: int
    symbol: str
    timestamp: str
    spot_price: Optional[float]
    expiry: Optional[str]
    days_to_expiry: Optional[int]
    atm_strike: Optional[float]
    atm_iv: Optional[float]
    atm_delta_call: Optional[float]
    atm_delta_put: Optional[float]
    atm_gamma: Optional[float]
    atm_vega: Optional[float]
    atm_theta: Optional[float]
    risk_free_rate: Optional[float]
    calls_count: Optional[int]
    puts_count: Optional[int]
    source: Optional[str]


class StrikeDetail(BaseModel):
    strike: float
    call_delta: Optional[float]
    put_delta: Optional[float]
    gamma: Optional[float]
    vega: Optional[float]
    theta: Optional[float]
    iv: Optional[float]
    call_oi: Optional[int]
    put_oi: Optional[int]


@router.get("/greeks/latest")
async def latest_options_greeks(symbol: Optional[str] = None):
    """Latest options Greeks snapshot. Optional ?symbol=SPY filter."""
    async with get_db() as db:
        if symbol:
            symbol = symbol.upper()
            cursor = await db.execute(
                """
                SELECT id, symbol, timestamp, spot_price, expiry, days_to_expiry,
                       atm_strike, atm_iv, atm_delta_call, atm_delta_put,
                       atm_gamma, atm_vega, atm_theta, risk_free_rate,
                       calls_count, puts_count, source
                FROM options_greeks
                WHERE symbol = ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (symbol,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, symbol, timestamp, spot_price, expiry, days_to_expiry,
                       atm_strike, atm_iv, atm_delta_call, atm_delta_put,
                       atm_gamma, atm_vega, atm_theta, risk_free_rate,
                       calls_count, puts_count, source
                FROM options_greeks
                ORDER BY timestamp DESC LIMIT 1
                """
            )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No options Greeks data{f' for {symbol}' if symbol else ''}")

        return {
            "id": row[0], "symbol": row[1], "timestamp": row[2],
            "spot_price": row[3], "expiry": row[4], "days_to_expiry": row[5],
            "atm_strike": row[6], "atm_iv": row[7],
            "atm_delta_call": row[8], "atm_delta_put": row[9],
            "atm_gamma": row[10], "atm_vega": row[11], "atm_theta": row[12],
            "risk_free_rate": row[13], "calls_count": row[14], "puts_count": row[15],
            "source": row[16],
        }


@router.get("/greeks/strikes")
async def options_strikes(symbol: str):
    """Per-strike Greeks detail for latest snapshot of given symbol."""
    symbol = symbol.upper()
    async with get_db() as db:
        snap_cursor = await db.execute(
            "SELECT id FROM options_greeks WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
            (symbol,),
        )
        snap_row = await snap_cursor.fetchone()
        if not snap_row:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        snap_id = snap_row[0]

        cursor = await db.execute(
            """
            SELECT strike, call_delta, put_delta, gamma, vega, theta, iv,
                   call_oi, put_oi
            FROM options_greeks_strikes
            WHERE snapshot_id = ?
            ORDER BY strike ASC
            """,
            (snap_id,),
        )
        rows = await cursor.fetchall()

    return {
        "symbol": symbol,
        "snapshot_id": snap_id,
        "strike_count": len(rows),
        "strikes": [
            {
                "strike": r[0],
                "call_delta": r[1],
                "put_delta": r[2],
                "gamma": r[3],
                "vega": r[4],
                "theta": r[5],
                "iv": r[6],
                "call_oi": r[7],
                "put_oi": r[8],
            }
            for r in rows
        ],
    }


@router.get("/greeks/all")
async def all_latest_greeks():
    """All symbols' latest ATM Greeks in one call (for dashboard)."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT symbol, timestamp, spot_price, expiry, days_to_expiry,
                   atm_strike, atm_iv, atm_delta_call, atm_delta_put,
                   atm_gamma, atm_vega, atm_theta
            FROM options_greeks
            WHERE id IN (
                SELECT MAX(id) FROM options_greeks GROUP BY symbol
            )
            ORDER BY symbol
            """
        )
        rows = await cursor.fetchall()
    return [
        {
            "symbol": r[0],
            "timestamp": r[1],
            "spot_price": r[2],
            "expiry": r[3],
            "days_to_expiry": r[4],
            "atm_strike": r[5],
            "atm_iv": r[6],
            "atm_delta_call": r[7],
            "atm_delta_put": r[8],
            "atm_gamma": r[9],
            "atm_vega": r[10],
            "atm_theta": r[11],
        }
        for r in rows
    ]