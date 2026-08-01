"""
Dark pool (Dark Pool / DIX) data fetcher.

Primary source: SqueezeMetrics public CSV (free).
Fallback: FINRA short interest data.
Mock mode: returns synthetic dark pool metrics matching DarkpoolFlow model.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


def _ema(values: list[float], span: int) -> list[float]:
    """Exponential moving average of a series (same definition as the
    backfill script). Used for EMA fast/slow + derived signals."""
    if not values:
        return []
    k = 2.0 / (span + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


class DarkpoolFetcher(BaseFetcher):
    """Fetches dark pool metrics: DIX, short ratios, EMA crossovers."""

    @property
    def source_name(self) -> str:
        return "dark_pool_metrics"

    @property
    def _mock_mode_key(self) -> str:
        # Darkpool fetcher pulls the public SqueezeMetrics DIX CSV (no key needed).
        # Mapping to "none" (not in config.is_mock_mode key_map) so it always hits
        # the live path and only falls back to mock when the CSV fetch fails.
        return "none"

    SQUEEZEMETRICS_CSV_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"

    async def fetch(self) -> dict:
        """Fetch dark pool data with fallback chain."""
        try:
            return await self._fetch_squeezemetrics()
        except Exception as e:
            self.logger.warning(f"SqueezeMetrics failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock dark pool metrics."""
        return self._generate_mock_data()

    async def _fetch_squeezemetrics(self) -> dict[str, Any]:
        """Fetch from SqueezeMetrics public DIX CSV.

        Returns:
            dict with today's metrics (for dark_pool_metrics daily PK table)
            + 'history' list (last 90 days for dark_pool_history table)
        """
        client = await self._get_client()
        resp = await client.get(self.SQUEEZEMETRICS_CSV_URL)
        resp.raise_for_status()

        # Parse CSV content
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            raise ValueError("SqueezeMetrics CSV has insufficient data")

        # Header: date,price,dix,gex
        # Rows are chronological ASC (2011-05-02 first, today last)
        latest = lines[-1].split(",")

        # Extract DIX value (column index 2: 0=date, 1=price, 2=dix, 3=gex)
        dix_value = float(latest[2]) if len(latest) > 2 else None
        gex_value = float(latest[3]) if len(latest) > 3 else None
        spx_price = float(latest[1]) if len(latest) > 1 else None

        # Compute the DIX signal from the real CSV value only.
        dix_signal = dix_value is not None and dix_value > 0.45

        # Build history (last 90 days for dark_pool_history table)
        history = []
        history_lines = lines[-90:] if len(lines) >= 90 else lines[1:]
        for line in history_lines:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                d = parts[0]
                p = float(parts[1]) if parts[1] else None
                dix = float(parts[2]) if parts[2] else None
                gex = float(parts[3]) if len(parts) > 3 and parts[3] else None
            except (ValueError, IndexError):
                continue
            history.append({
                "date": d,
                "timestamp": f"{d}T16:00:00+00:00",  # Market close proxy
                "dix_value": dix * 100 if dix is not None else None,  # CSV is 0-1, scale to % for consistency
                "gex_value": gex,
                "spx_price": p,
                "chartexchange_short_ratio": None,  # not in CSV
                "source": "squeezemetrics",
            })

        # 2026-08-02: compute all derivable fields from the REAL DIX/SPX series
        # (same formulas as scripts/backfill_vix_darkpool_history.py) so every
        # live cycle repopulates the rich row instead of wiping it to None.
        derived = self._compute_derived(history, dix_value=dix_value)
        slopes = self._compute_spx_slopes(history)

        return {
            "date": date.today().isoformat(),
            "dix_value": dix_value * 100 if dix_value is not None else None,  # scale to %
            "gex_value": gex_value,
            "spx_price": spx_price,
            "chartexchange_short_ratio": None,  # requires paid ChartExchange key (no free source)
            "stockgrid_20d_slope": slopes["slope_20d"],
            "stockgrid_60d_slope": slopes["slope_60d"],
            "stockgrid_divergence": False,
            "dbmf_ma5_recovery": False,
            "dix_signal": derived["dix_signal"],
            "short_ratio_signal": False,
            "stockgrid_signal": False,
            "aggregated_signal": derived["aggregated_signal"],
            "v_net": derived["v_net"],
            "ema_fast_5": derived["ema_fast_5"],
            "ema_slow_20": derived["ema_slow_20"],
            "zero_cross_signal": derived["zero_cross_signal"],
            "momentum_reversal_signal": derived["momentum_reversal_signal"],
            "history": history,
        }

    def _compute_derived(self, history: list[dict], dix_value: Optional[float]) -> dict:
        """Compute v_net / EMA / crossovers from the real DIX series.

        Mirrors scripts/backfill_vix_darkpool_history.py.backfill_darkpool:
          v_net = (DIX - 50) * 20
          ema_fast_5 = EMA(v_net, 5), ema_slow_20 = EMA(v_net, 20)
        Falls back to a single-point extrapolation when history is short.
        """
        # Build a DIX-percent series (oldest -> newest)
        dix_series: list[float] = []
        for h in history:
            if h.get("dix_value") is not None:
                dix_series.append(float(h["dix_value"]))
        # Ensure the latest live value is included even if not in 90d slice
        if dix_value is not None:
            scaled = dix_value * 100
            if not dix_series or abs(dix_series[-1] - scaled) > 1e-9:
                dix_series.append(scaled)

        if not dix_series:
            return {
                "v_net": None, "ema_fast_5": None, "ema_slow_20": None,
                "dix_signal": False, "aggregated_signal": False,
                "zero_cross_signal": None, "momentum_reversal_signal": None,
            }

        v_net_series = [(d - 50.0) * 20.0 for d in dix_series]
        ema_fast = _ema(v_net_series, 5)
        ema_slow = _ema(v_net_series, 20)

        i = len(dix_series) - 1
        vn = v_net_series[i]
        ef = ema_fast[i]
        es = ema_slow[i]
        aggregated = dix_series[i] > 50.0
        zero_cross = "bullish_cross" if ef > es else "bearish_cross"
        reversal = (
            "reversal_up" if (ef < es and vn > ef)
            else ("reversal_down" if (ef > es and vn < ef) else None)
        )
        return {
            "v_net": round(vn, 2),
            "ema_fast_5": round(ef, 2),
            "ema_slow_20": round(es, 2),
            "dix_signal": aggregated,
            "aggregated_signal": aggregated,
            "zero_cross_signal": zero_cross,
            "momentum_reversal_signal": reversal,
        }

    def _compute_spx_slopes(self, history: list[dict]) -> dict:
        """Compute 20d / 60d slope of the real SPX price series via linear fit.

        Slope = normalized linear coefficient of a least-squares fit over the
        last N trading days of SPX close (from the SqueezeMetrics CSV). A real,
        key-free positioning-trend proxy that replaces the old random mock.
        Returns None when insufficient data.
        """
        prices = [float(h["spx_price"]) for h in history if h.get("spx_price") is not None]
        out = {"slope_20d": None, "slope_60d": None}
        if len(prices) < 5:
            return out
        try:
            import numpy as np
        except ImportError:
            return out

        def _fit(n: int) -> Optional[float]:
            seg = prices[-n:] if len(prices) >= n else prices
            if len(seg) < 3:
                return None
            x = np.arange(len(seg), dtype=float)
            y = np.asarray(seg, dtype=float)
            slope = float(np.polyfit(x, y, 1)[0])
            # normalize by price level so 20d/60d are comparable
            return round(slope / y[-1], 5)

        out["slope_20d"] = _fit(20)
        out["slope_60d"] = _fit(60)
        return out

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock dark pool metrics."""
        dix_value = random.uniform(40.0, 60.0)
        short_ratio = random.uniform(1.5, 4.5)
        v_net = random.uniform(-500, 500)
        ema_fast = random.uniform(-200, 200)
        ema_slow = random.uniform(-300, 300)

        dix_signal = dix_value > 50.0
        short_signal = short_ratio > 3.5
        zero_cross = "bullish_cross" if ema_fast > ema_slow else "bearish_cross"

        return {
            "date": date.today().isoformat(),
            "dix_value": round(dix_value, 2),
            "chartexchange_short_ratio": round(short_ratio, 2),
            "stockgrid_20d_slope": round(random.uniform(-0.5, 0.5), 4),
            "stockgrid_60d_slope": round(random.uniform(-0.3, 0.3), 4),
            "stockgrid_divergence": random.random() < 0.2,
            "dbmf_ma5_recovery": random.random() < 0.3,
            "dix_signal": dix_signal,
            "short_ratio_signal": short_signal,
            "stockgrid_signal": random.random() < 0.25,
            "aggregated_signal": dix_signal and short_signal,
            "v_net": round(v_net, 2),
            "ema_fast_5": round(ema_fast, 2),
            "ema_slow_20": round(ema_slow, 2),
            "zero_cross_signal": zero_cross,
            "momentum_reversal_signal": random.choice(["reversal_up", "reversal_down", None]),
        }
