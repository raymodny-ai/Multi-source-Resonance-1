"""
Macroeconomic data fetcher.

Collects macro indicators: Treasury yields, Fed funds rate, USD index (DXY),
credit spreads, yield curve slope, economic data releases.
Primary source: FRED API (requires key) or public Treasury data.
Mock mode: returns synthetic macro data.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class MacroFetcher(BaseFetcher):
    """Fetches macroeconomic indicators."""

    @property
    def source_name(self) -> str:
        return "macro_data"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # Always mock by default (FRED key not in config)

    # FRED API (optional — requires FRED_API_KEY env var)
    FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

    async def fetch(self) -> dict:
        """Fetch macro data."""
        # Try FRED API
        try:
            return await self._fetch_fred()
        except Exception as e:
            self.logger.warning(f"FRED fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock macro data."""
        return self._generate_mock_data()

    async def _fetch_fred(self) -> dict[str, Any]:
        """Fetch from FRED API (requires FRED_API_KEY env var)."""
        import os

        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED_API_KEY not set")

        # Fetch key series
        series_map = {
            "DGS10": "treasury_10y",
            "DGS2": "treasury_2y",
            "DGS30": "treasury_30y",
            "DTWEXBGS": "dxy_index",
            "BAMLC0A4CBBB": "credit_spread_bbb",
            "FEDFUNDS": "fed_funds_rate",
        }

        results = {}
        for series_id, key in series_map.items():
            data = await self._get_json(
                self.FRED_URL,
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            obs = data.get("observations", [])
            if obs:
                val = obs[0].get("value", ".")
                results[key] = float(val) if val != "." else None
            else:
                results[key] = None

        # Compute derived indicators
        yield_curve = None
        if results.get("treasury_10y") is not None and results.get("treasury_2y") is not None:
            yield_curve = results["treasury_10y"] - results["treasury_2y"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "treasury_2y": results.get("treasury_2y"),
            "treasury_10y": results.get("treasury_10y"),
            "treasury_30y": results.get("treasury_30y"),
            "yield_curve_slope": yield_curve,
            "yield_curve_signal": self._interpret_yield_curve(yield_curve),
            "fed_funds_rate": results.get("fed_funds_rate"),
            "dxy_index": results.get("dxy_index"),
            "credit_spread_bbb": results.get("credit_spread_bbb"),
            "is_recession_risk": yield_curve is not None and yield_curve < 0,
        }

    def _interpret_yield_curve(self, slope: float | None) -> str:
        """Interpret yield curve slope."""
        if slope is None:
            return "unknown"
        if slope < -0.5:
            return "deep_inversion"  # Strong recession signal
        elif slope < 0:
            return "inverted"
        elif slope < 0.5:
            return "flat"
        elif slope < 2.0:
            return "normal"
        else:
            return "steep"

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock macro data."""
        treasury_2y = round(random.uniform(3.5, 5.5), 3)
        treasury_10y = round(treasury_2y + random.uniform(-1.0, 1.5), 3)
        treasury_30y = round(treasury_10y + random.uniform(0.2, 1.0), 3)
        yield_curve = round(treasury_10y - treasury_2y, 3)
        fed_funds = round(random.uniform(4.25, 5.50), 2)
        dxy = round(random.uniform(98, 108), 2)
        credit_spread = round(random.uniform(0.8, 2.5), 2)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "treasury_2y": treasury_2y,
            "treasury_10y": treasury_10y,
            "treasury_30y": treasury_30y,
            "yield_curve_slope": yield_curve,
            "yield_curve_signal": self._interpret_yield_curve(yield_curve),
            "fed_funds_rate": fed_funds,
            "dxy_index": dxy,
            "credit_spread_bbb": credit_spread,
            "is_recession_risk": yield_curve < 0,
        }
