"""
SqueezeMetrics dark pool fetcher (DIX / GEX / flip zone / put wall).

Fetches the free public SqueezeMetrics DIX+GEX CSV and derives the
GEX-page metrics from the REAL SPX close price in that CSV (AUDIT-MOCK-002 P0).

Data contract (AUDIT-MOCK-002 P0 #1): the live path MUST NOT inject any
random values. put_wall / flip_zone / gex_calibrated are computed from the
real CSV price/gex via the same ratios as scripts/backfill_gex_history.py:
    gex_calibrated = gex_local * 0.95
    put_wall       = spot_price * 0.96
    flip_zone_lower/upper = spot_price * 0.97 / 1.03

Source: https://squeezemetrics.com/monitor/static/DIX.csv (free public CSV)
Fallback: Returns mock data (is_mock=1) only when the CSV fetch fails.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class SqueezeMetricsFetcher(BaseFetcher):
    """Fetches SqueezeMetrics DIX/GEX data from public CSV."""

    @property
    def source_name(self) -> str:
        return "squeezemetrics"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # public data — no key gating (mock only on fetch failure)

    CSV_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"

    # Calibration ratios (must match scripts/backfill_gex_history.py)
    GEX_CALIBRATION_RATIO = 0.95
    PUT_WALL_RATIO = 0.96
    FLIP_ZONE_LOWER_RATIO = 0.97
    FLIP_ZONE_UPPER_RATIO = 1.03

    def _is_mock_mode(self) -> bool:
        return False

    async def fetch(self) -> dict:
        """Fetch SqueezeMetrics DIX + GEX data."""
        try:
            return await self._fetch_csv()
        except Exception as e:
            self.logger.warning(f"SqueezeMetrics fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        return self._generate_mock_data()

    async def _fetch_csv(self) -> dict[str, Any]:
        """Parse SqueezeMetrics public DIX+GEX CSV (date,price,dix,gex).

        Rows are chronological ASC — the latest is the LAST row (unlike the
        old code which wrongly read lines[1] as latest).
        """
        client = await self._get_client()
        resp = await client.get(self.CSV_URL)
        resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            raise ValueError("SqueezeMetrics CSV has insufficient data")

        latest = lines[-1].split(",")
        # Typical columns: date, price, dix, gex  (AUDIT verified)
        try:
            price = float(latest[1]) if len(latest) > 1 and latest[1] else None
            dix_value = float(latest[2]) if len(latest) > 2 and latest[2] else None
            gex_value = float(latest[3]) if len(latest) > 3 and latest[3] else None
        except (ValueError, IndexError):
            price = dix_value = gex_value = None

        # AUDIT-MOCK-002 P0 #1: derive GEX-page metrics from the REAL SPX price
        # (no random). put_wall / flip_zone are absolute price levels.
        if price:
            put_wall = round(price * self.PUT_WALL_RATIO, 2)
            flip_lower = round(price * self.FLIP_ZONE_LOWER_RATIO, 2)
            flip_upper = round(price * self.FLIP_ZONE_UPPER_RATIO, 2)
        else:
            put_wall = flip_lower = flip_upper = None

        return {
            "date": date.today().isoformat(),
            "dix_value": dix_value,
            "gex_local": gex_value,
            "gex_calibrated": round(gex_value * self.GEX_CALIBRATION_RATIO, 2) if gex_value else None,
            "alpha_factor": 1.0,
            "put_wall_level": put_wall,
            "flip_zone_lower": flip_lower,
            "flip_zone_upper": flip_upper,
            # short ratio / stockgrid slope are fed by darkpool_fetcher / finra —
            # this fetcher's CSV has no such columns, so they stay honest None.
            "chartexchange_short_ratio": None,
            "stockgrid_slope": None,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Synthetic mock — ONLY used when the real CSV fetch fails (is_mock=1)."""
        gex = random.uniform(-2000000, 2000000)
        return {
            "date": date.today().isoformat(),
            "dix_value": round(random.uniform(40.0, 60.0), 2),
            "gex_local": round(gex, 2),
            "gex_calibrated": round(gex * 0.95, 2),
            "alpha_factor": 1.0,
            "put_wall_level": round(random.uniform(5200, 5600), 0),
            "flip_zone_lower": round(random.uniform(5300, 5500), 0),
            "flip_zone_upper": round(random.uniform(5500, 5700), 0),
            "chartexchange_short_ratio": round(random.uniform(1.5, 4.0), 2),
            "stockgrid_slope": round(random.uniform(-0.5, 0.5), 4),
        }
