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

        # FIX-13: fields unavailable from SqueezeMetrics are explicitly absent.
        # Downstream analyzers skip ``None`` inputs instead of scoring fabricated
        # random values as if they were real market observations.
        return {
            "date": date.today().isoformat(),
            "dix_value": dix_value * 100 if dix_value is not None else None,  # scale to %
            "gex_value": gex_value,
            "spx_price": spx_price,
            "chartexchange_short_ratio": None,
            "stockgrid_20d_slope": None,
            "stockgrid_60d_slope": None,
            "stockgrid_divergence": False,
            "dbmf_ma5_recovery": False,
            "dix_signal": dix_signal,
            "short_ratio_signal": False,
            "stockgrid_signal": False,
            "aggregated_signal": dix_signal,
            "v_net": None,
            "ema_fast_5": None,
            "ema_slow_20": None,
            "zero_cross_signal": None,
            "momentum_reversal_signal": None,
            "history": history,
        }

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
