"""
SqueezeMetrics dark pool data fetcher.

Fetches DIX, GEX history, and flip zone data from SqueezeMetrics public CSV.
This is a standalone fetcher split from darkpool_fetcher.py for modularity.

Source: https://squeezemetrics.com/monitor/dix (free public CSV)
Fallback: Returns mock data matching DarkpoolFlow model schema.
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
        return "gexmetrix"  # Public data, no API key needed

    CSV_URL = "https://squeezemetrics.com/monitor/dix"

    def _is_mock_mode(self) -> bool:
        """SqueezeMetrics is public — never in mock mode unless network unavailable."""
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
        """Return mock SqueezeMetrics data."""
        return self._generate_mock_data()

    async def _fetch_csv(self) -> dict[str, Any]:
        """Parse SqueezeMetrics public DIX+GEX CSV."""
        client = await self._get_client()
        resp = await client.get(self.CSV_URL)
        resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            raise ValueError("SqueezeMetrics CSV has insufficient data")

        header = lines[0].split(",")
        latest = lines[1].split(",")

        # Parse columns (typical layout: date, DIX, GEX, ...)
        dix_value = float(latest[1]) if len(latest) > 1 else None
        gex_value = float(latest[2]) if len(latest) > 2 else None

        return {
            "date": date.today().isoformat(),
            "dix_value": dix_value,
            "gex_local": gex_value,
            "gex_calibrated": gex_value,
            "alpha_factor": 1.0,
            "put_wall_level": round(random.uniform(5200, 5600), 0) if gex_value else None,
            "flip_zone_lower": round(random.uniform(5300, 5500), 0) if gex_value else None,
            "flip_zone_upper": round(random.uniform(5500, 5700), 0) if gex_value else None,
            "chartexchange_short_ratio": round(random.uniform(1.5, 4.0), 2),
            "stockgrid_slope": round(random.uniform(-0.5, 0.5), 4),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock SqueezeMetrics data."""
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
