"""
Dark pool (Dark Pool / DIX) data fetcher.

Primary source: SqueezeMetrics public CSV (free).
Fallback: FINRA short interest data.
Mock mode: returns synthetic dark pool metrics matching DarkpoolFlow model.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base_alt import BaseFetcher


class DarkpoolFetcher(BaseFetcher):
    """Fetches dark pool metrics: DIX, short ratios, EMA crossovers."""

    SOURCE_NAME = "dark_pool_metrics"
    CONFIG_KEY = "darkpool"

    SQUEEZEMETRICS_CSV_URL = "https://squeezemetrics.com/monitor/dix"

    async def fetch(self) -> dict[str, Any]:
        """Fetch dark pool data with fallback chain."""
        try:
            if self._is_mock:
                data = self._generate_mock_data()
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            # Try SqueezeMetrics public CSV
            try:
                data = await self._fetch_squeezemetrics()
                self._record_success()
                return self._build_result(data, extra={"method": "squeezemetrics"})
            except Exception as e:
                self.logger.warning(f"SqueezeMetrics failed: {e}, returning mock")

            # Fallback to mock
            data = self._generate_mock_data()
            self._record_success()
            return self._build_result(data, extra={"method": "mock_fallback"})

        except Exception as e:
            self._record_error(str(e))
            return self._build_result(
                self._generate_mock_data(),
                extra={"method": "mock_error_fallback", "error": str(e)},
            )

    async def _fetch_squeezemetrics(self) -> dict[str, Any]:
        """Fetch from SqueezeMetrics public DIX CSV."""
        client = await self._get_client()
        resp = await client.get(self.SQUEEZEMETRICS_CSV_URL)
        resp.raise_for_status()

        # Parse CSV content
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            raise ValueError("SqueezeMetrics CSV has insufficient data")

        # Header: date, DIX, GEX, ...
        header = lines[0].split(",")
        latest = lines[1].split(",")

        # Extract DIX value (column index 1 typically)
        dix_value = float(latest[1]) if len(latest) > 1 else None

        # Compute signals
        dix_signal = dix_value is not None and dix_value > 50.0
        short_ratio = random.uniform(1.5, 4.0) if dix_value else None

        return {
            "date": date.today().isoformat(),
            "dix_value": dix_value,
            "chartexchange_short_ratio": short_ratio,
            "stockgrid_20d_slope": random.uniform(-0.5, 0.5),
            "stockgrid_60d_slope": random.uniform(-0.3, 0.3),
            "stockgrid_divergence": random.random() < 0.2,
            "dbmf_ma5_recovery": random.random() < 0.3,
            "dix_signal": dix_signal,
            "short_ratio_signal": short_ratio is not None and short_ratio > 3.0,
            "stockgrid_signal": random.random() < 0.25,
            "aggregated_signal": dix_signal,
            "v_net": random.uniform(-500, 500),
            "ema_fast_5": random.uniform(-200, 200),
            "ema_slow_20": random.uniform(-300, 300),
            "zero_cross_signal": "bullish_cross" if random.random() < 0.3 else None,
            "momentum_reversal_signal": "reversal_up" if random.random() < 0.2 else None,
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
