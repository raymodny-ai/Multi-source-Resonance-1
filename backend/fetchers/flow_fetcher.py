"""
Money flow data fetcher (option B: honest semantic subscription).

Collects money flow indicators. Per Owner decision (2026-08-02, option B):
  - Compute what is HONESTLY derivable from a free source — here Chaikin
    Money Flow (CMF) for a market-proxy ETF (SPY) from yfinance OHLCV.
    CMF is a genuine A-class "money flow" measure (volume-price pressure).
  - Field that requires PAID institutional/retail/dark-pool data (B-class:
    ChartExchange / FMP / RenkoRadar) are set to None (honest "invalid") —
    we never fabricate institutional/retail/dark-pool figures.

Was previously ALWAYS mock with random net/institutional/retail/dark_pool
values. Now: real CMF on the live path, NULL for paid-only semantics.
Fallback: mock ONLY on fetch failure (tagged _internal_mock).

NOTE: money_flow currently has NO table/writer/analyzer consumer (dead data
path — output lands in gateway_snapshots audit only). This fix guarantees the
values it would emit are honest; wiring a consumer is a separate decision.
"""

import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from backend.fetchers.base import BaseFetcher


# Market-proxy symbol used to compute Chaikin Money Flow
CMF_SYMBOL = "SPY"
CMF_PERIOD = 20  # standard 20-day Chaikin Money Flow

_CMF_CACHE: Optional[tuple[dict[str, Any], float]] = None
_CMF_CACHE_TTL = 900  # 15 min — intraday pressure, refresh more often than daily


class FlowFetcher(BaseFetcher):
    """Fetches an honest, free-derived money flow indicator (CMF)."""

    @property
    def source_name(self) -> str:
        return "money_flow"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # public data — hit live, mock only on fetch failure

    def _is_mock_mode(self) -> bool:
        """yfinance CMF is public — never in mock mode unless network fails."""
        return False

    async def fetch(self) -> dict:
        """Fetch real Chaikin Money Flow for SPY."""
        try:
            return await self._fetch_cmf()
        except Exception as e:
            self.logger.warning(f"Flow(yfinance CMF) fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock money flow data (full-mock fallback only)."""
        return self._generate_mock_data()

    async def _fetch_cmf(self) -> dict[str, Any]:
        """Compute Chaikin Money Flow for a market proxy (SPY) from yfinance."""
        global _CMF_CACHE
        now = time.time()
        if _CMF_CACHE and (now - _CMF_CACHE[1]) < _CMF_CACHE_TTL:
            return _CMF_CACHE[0]

        import yfinance as yf
        import pandas as pd

        def _blocking() -> dict[str, Any]:
            df = yf.download(
                CMF_SYMBOL, period="3mo", progress=False, auto_adjust=True,
            )
            if df is None or len(df) < CMF_PERIOD:
                raise RuntimeError("yfinance returned insufficient data")
            o = np.asarray(df["Open"].squeeze(), dtype=float).reshape(-1)
            h = np.asarray(df["High"].squeeze(), dtype=float).reshape(-1)
            l = np.asarray(df["Low"].squeeze(), dtype=float).reshape(-1)
            c = np.asarray(df["Close"].squeeze(), dtype=float).reshape(-1)
            v = np.asarray(df["Volume"].squeeze(), dtype=float).reshape(-1)

            # Chaikin Money Flow: sum(MFM*Vol)/sum(Vol) over the window
            hl = (h - l).copy()
            hl[hl == 0] = 1e-9  # avoid div-by-zero on flat bars
            mfm = ((c - l) - (h - c)) / hl          # Money Flow Multiplier, [-1,1]
            mfv = mfm * v                            # Money Flow Volume
            n = len(c)
            cmf = float(mfv[-CMF_PERIOD:].sum() / v[-CMF_PERIOD:].sum()) if n >= CMF_PERIOD else 0.0
            # scale CMF [-1,1] -> net_money_flow ±1000 (direction+strength readable)
            net = cmf * 1000.0

            last = float(c[-1])
            return {
                # Real A-class derivative (CMF, free)
                "net_money_flow": round(net, 2),
                "cmf_signal": "accumulation" if cmf > 0.0 else ("distribution" if cmf < 0.0 else "neutral"),
                "cmf_period": CMF_PERIOD,
                "symbol": CMF_SYMBOL,
                "last_close": round(last, 2),
                "source": "yfinance",
                # Paid-only B-class semantics — honestly invalid (no paid key)
                "institutional_flow": None,
                "retail_flow": None,
                "dark_pool_net_volume": None,
                "block_trade_volume": None,
                "consecutive_inflow_days": None,
                # Derived only from the real CMF
                "flow_direction": "inflow" if net > 0 else ("outflow" if net < 0 else "flat"),
                "flow_strength": round(abs(cmf), 4),      # 0-1
                "is_accumulation": bool(cmf > 0.02),
            }

        result = await asyncio.to_thread(_blocking)
        _CMF_CACHE = (result, now)
        return result

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock money flow data (full-mock fallback only)."""
        net_flow = random.uniform(-1000, 1000)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "net_money_flow": round(net_flow, 2),
            "cmf_signal": "accumulation" if net_flow > 0 else ("distribution" if net_flow < 0 else "neutral"),
            "cmf_period": CMF_PERIOD,
            "symbol": CMF_SYMBOL,
            "last_close": None,
            "source": "mock",
            "institutional_flow": None,
            "retail_flow": None,
            "dark_pool_net_volume": None,
            "block_trade_volume": None,
            "consecutive_inflow_days": random.randint(0, 8),
            "flow_direction": "inflow" if net_flow > 0 else "outflow",
            "flow_strength": round(abs(net_flow) / 1000.0, 4),
            "is_accumulation": net_flow > 250,
        }
