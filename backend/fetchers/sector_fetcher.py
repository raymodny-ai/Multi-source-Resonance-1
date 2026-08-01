"""
Sector rotation data fetcher (real-data version).

Collects sector performance data: relative strength of S&P 500 sector ETFs,
rotation signals, defensive vs cyclical leadership.

Source history:
- 2026-08-02: was ALWAYS mock (no dedicated free API wired). Now pulls real
  daily/weekly/monthly returns from yfinance sector ETFs (free, keyless),
  same proven dependency as darkpool short_ratio / stockgrid slopes.
  The 11 S&P sector ETFs (XLK/XLF/XLV/XLE/XLI/XLY/XLP/XLU/XLB/XLRE/XLC)
  already existed in the SECTOR_ETFS map — only the fetch logic was fake.

Fallback: Returns mock data ONLY on fetch failure (tagged _internal_mock),
never on the real path.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np

from backend.fetchers.base import BaseFetcher


# S&P 500 sector ETFs
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

# Defensive sectors (risk-off leadership)
DEFENSIVE_SECTORS = {"XLU", "XLP", "XLV"}
CYCLICAL_SECTORS = {"XLE", "XLI", "XLY", "XLB", "XLK", "XLF"}

# Sector closes move slowly vs daily noise — 1h cache keeps each pipeline
# cycle from re-hitting yfinance (11 downloads per cycle is wasteful).
_SECTOR_CACHE: Optional[tuple[dict[str, float], float]] = None  # (result_map, fetch_ts)
_SECTOR_CACHE_TTL = 3600


class SectorFetcher(BaseFetcher):
    """Fetches real sector rotation data from yfinance sector ETFs."""

    @property
    def source_name(self) -> str:
        return "sector_rotation"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # public data — no key gating (hit live, mock only on failure)

    # yfinance lookbacks: 1y gives stable weekly (≈52w) + monthly (≈12m) spans
    LOOKBACK_YEARS = 1

    def _is_mock_mode(self) -> bool:
        """Sector ETFs are public — never in mock mode unless network fails."""
        return False

    async def fetch(self) -> dict:
        """Fetch real sector ETF returns via yfinance."""
        try:
            return await self._fetch_sector_data()
        except Exception as e:
            self.logger.warning(f"Sector(yfinance) fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock sector rotation data (full-mock fallback only)."""
        return self._generate_mock_data()

    async def _fetch_sector_data(self) -> dict[str, Any]:
        """Compute daily/weekly/monthly return per sector ETF via yfinance.

        Returns the same schema as the old mock generator, but with REAL
        numbers derived from yfinance Close history. No random in this path.
        """
        global _SECTOR_CACHE
        now = time.time()
        if _SECTOR_CACHE and (now - _SECTOR_CACHE[1]) < _SECTOR_CACHE_TTL:
            raw = _SECTOR_CACHE[0]
        else:
            import yfinance as yf

            def _download() -> dict[str, dict]:
                end = datetime.now(timezone.utc).date()
                start = end - timedelta(days=int(self.LOOKBACK_YEARS * 365) + 10)
                out: dict[str, dict] = {}
                for etf in SECTOR_ETFS:
                    try:
                        df = yf.download(
                            etf, start=start.isoformat(), end=end.isoformat(),
                            progress=False, auto_adjust=True,
                        )
                        if df is None or len(df) < 5:
                            out[etf] = {}
                            continue
                        closes = df["Close"].squeeze()
                        # guard: single-row/multi-level can yield 2D; flatten to 1D
                        c = np.asarray(closes, dtype=float).reshape(-1)
                        if c.size < 5:
                            out[etf] = {}
                            continue
                        idx = list(closes.index)
                        out[etf] = {
                            "closes": c,
                            "dates": [i.date().isoformat() for i in idx],
                        }
                    except Exception as exc:
                        self.logger.warning(f"[sector:yfinance] {etf} failed: {exc}")
                        out[etf] = {}
                return out

            raw = await asyncio.to_thread(_download)
            _SECTOR_CACHE = (raw, now)

        sector_perf: dict[str, Any] = {}
        for etf, name in SECTOR_ETFS.items():
            d = raw.get(etf) or {}
            c = d.get("closes")
            if c is None or np.size(c) < 5:
                sector_perf[etf] = {
                    "name": name, "daily_return": None, "weekly_return": None,
                    "monthly_return": None,
                }
                continue
            last = c[-1]
            daily = (last / c[-2] - 1) * 100 if len(c) >= 2 else None
            weekly = (last / c[-6] - 1) * 100 if len(c) >= 6 else None
            monthly = (last / c[-22] - 1) * 100 if len(c) >= 22 else None
            sector_perf[etf] = {
                "name": name,
                "daily_return": round(float(daily), 2) if daily is not None else None,
                "weekly_return": round(float(weekly), 2) if weekly is not None else None,
                "monthly_return": round(float(monthly), 2) if monthly is not None else None,
            }

        # Leadership = best/worst among sectors with a real daily return
        real_daily = {k: v["daily_return"] for k, v in sector_perf.items()
                      if v["daily_return"] is not None}
        if real_daily:
            best = max(real_daily.items(), key=lambda kv: kv[1])
            worst = min(real_daily.items(), key=lambda kv: kv[1])
            best_sector = {"etf": best[0], "return": best[1]}
            worst_sector = {"etf": worst[0], "return": worst[1]}
        else:
            best_sector = worst_sector = {"etf": None, "return": None}

        # Defensive vs cyclical averages over real daily returns
        def _avg(syms: set[str]) -> Optional[float]:
            vals = [sector_perf[s]["daily_return"] for s in syms
                    if sector_perf.get(s, {}).get("daily_return") is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        defensive_avg = _avg(DEFENSIVE_SECTORS)
        cyclical_avg = _avg(CYCLICAL_SECTORS)

        # Rotation signal (same thresholds as old logic, now on real numbers)
        rotation_signal = "neutral"
        if defensive_avg is not None and cyclical_avg is not None:
            if defensive_avg > cyclical_avg + 1.0:
                rotation_signal = "risk_off"
            elif cyclical_avg > defensive_avg + 1.0:
                rotation_signal = "risk_on"

        daily_vals = [v["daily_return"] for v in sector_perf.values()
                      if v["daily_return"] is not None]
        breadth_positive = (
            sum(1 for v in daily_vals if v > 0) > 5 if daily_vals else None
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sector_performance": sector_perf,
            "best_sector": best_sector,
            "worst_sector": worst_sector,
            "defensive_avg_return": defensive_avg,
            "cyclical_avg_return": cyclical_avg,
            "rotation_signal": rotation_signal,
            "breadth_positive": breadth_positive,
            "source": "yfinance",
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock sector rotation data (full-mock fallback only)."""
        sector_perf = {}
        for etf, name in SECTOR_ETFS.items():
            sector_perf[etf] = {
                "name": name,
                "daily_return": round(random.uniform(-3.0, 3.0), 2),
                "weekly_return": round(random.uniform(-5.0, 5.0), 2),
                "monthly_return": round(random.uniform(-8.0, 8.0), 2),
            }

        best_sector = max(sector_perf.items(), key=lambda x: x[1]["daily_return"])
        worst_sector = min(sector_perf.items(), key=lambda x: x[1]["daily_return"])

        defensive_avg = sum(
            sector_perf[s]["daily_return"] for s in DEFENSIVE_SECTORS if s in sector_perf
        ) / len(DEFENSIVE_SECTORS)
        cyclical_avg = sum(
            sector_perf[s]["daily_return"] for s in CYCLICAL_SECTORS if s in sector_perf
        ) / len(CYCLICAL_SECTORS)

        if defensive_avg > cyclical_avg + 1.0:
            rotation_signal = "risk_off"
        elif cyclical_avg > defensive_avg + 1.0:
            rotation_signal = "risk_on"
        else:
            rotation_signal = "neutral"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sector_performance": sector_perf,
            "best_sector": {"etf": best_sector[0], "return": best_sector[1]["daily_return"]},
            "worst_sector": {"etf": worst_sector[0], "return": worst_sector[1]["daily_return"]},
            "defensive_avg_return": round(defensive_avg, 2),
            "cyclical_avg_return": round(cyclical_avg, 2),
            "rotation_signal": rotation_signal,
            "breadth_positive": sum(1 for s in sector_perf.values() if s["daily_return"] > 0) > 5,
        }
