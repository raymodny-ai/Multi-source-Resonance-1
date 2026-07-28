"""
VIX term structure data fetcher.

Collects VIX spot, VX1 (1-month), VX2 (2-month) futures, term structure
ratio and state (contango / backwardation / flat).
Primary source: CBOE public CDN (free, no key).
Mock mode: returns synthetic VIX term structure data matching VIXSnapshot model.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base_alt import BaseFetcher


class VIXTermFetcher(BaseFetcher):
    """Fetches VIX term structure data from CBOE."""

    SOURCE_NAME = "vix_term_structure"
    CONFIG_KEY = ""  # CBOE public data is free

    CBOE_VIX_URL = "https://cdn.cboe.com/api/us/daily_market_statistics/vix_term_structure.json"

    async def fetch(self) -> dict[str, Any]:
        """Fetch VIX term structure data."""
        try:
            if self._is_mock:
                data = self._generate_mock_data()
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            # Try CBOE public data
            try:
                data = await self._fetch_cboe()
                self._record_success()
                return self._build_result(data, extra={"method": "cboe"})
            except Exception as e:
                self.logger.warning(f"CBOE VIX fetch failed: {e}, returning mock")

            data = self._generate_mock_data()
            self._record_success()
            return self._build_result(data, extra={"method": "mock_fallback"})

        except Exception as e:
            self._record_error(str(e))
            return self._build_result(
                self._generate_mock_data(),
                extra={"method": "mock_error", "error": str(e)},
            )

    async def _fetch_cboe(self) -> dict[str, Any]:
        """Fetch from CBOE public CDN."""
        raw = await self._get_json(self.CBOE_VIX_URL)

        # Parse latest entry
        latest = raw[-1] if isinstance(raw, list) and raw else {}
        vix_spot = float(latest.get("vix_spot", 0))
        vx1 = float(latest.get("vx1", 0))
        vx2 = float(latest.get("vx2", 0))

        # Compute term structure
        ts_ratio = (vx2 / vx1 - 1) if vx1 > 0 else 0.0
        if ts_ratio > 0.02:
            ts_state = "contango"
        elif ts_ratio < -0.02:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        panic_premium = vix_spot - vx1 if vix_spot and vx1 else 0.0

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vix_spot": vix_spot,
            "vx1": vx1,
            "vx2": vx2,
            "term_structure_ratio": round(ts_ratio, 4),
            "term_structure_state": ts_state,
            "panic_premium": round(panic_premium, 2),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock VIX term structure data."""
        vix_spot = round(random.uniform(12, 35), 2)
        vx1 = round(vix_spot + random.uniform(-2, 3), 2)
        vx2 = round(vx1 + random.uniform(-1, 4), 2)

        ts_ratio = (vx2 / vx1 - 1) if vx1 > 0 else 0.0
        if ts_ratio > 0.02:
            ts_state = "contango"
        elif ts_ratio < -0.02:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        panic_premium = round(vix_spot - vx1, 2)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vix_spot": vix_spot,
            "vx1": vx1,
            "vx2": vx2,
            "term_structure_ratio": round(ts_ratio, 4),
            "term_structure_state": ts_state,
            "panic_premium": panic_premium,
        }
