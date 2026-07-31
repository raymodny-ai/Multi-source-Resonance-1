"""
CCData cryptocurrency derivatives data fetcher.

Fetches crypto derivatives data from CCData API as a fallback
when Hyperliquid is unavailable. Requires CCData_API_KEY.

Source: https://ccdata.com (crypto derivatives aggregation)
Fallback: Returns mock data matching crypto_derivatives model schema.
"""

import os
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class CCDataFetcher(BaseFetcher):
    """Fetches CCData crypto derivatives data (fallback for Hyperliquid)."""

    @property
    def source_name(self) -> str:
        return "ccdata"

    @property
    def _mock_mode_key(self) -> str:
        return "crypto"

    CCDATA_API_URL = "https://api.ccdata.com/v1/derivatives"

    def _is_mock_mode(self) -> bool:
        """Mock mode when CCData API key is absent."""
        return not bool(os.environ.get("CCDATA_API_KEY"))

    async def fetch(self) -> dict:
        """Fetch CCData crypto derivatives data."""
        try:
            return await self._fetch_ccdata()
        except Exception as e:
            self.logger.warning(f"CCData fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock crypto derivatives data."""
        return self._generate_mock_data()

    async def _fetch_ccdata(self) -> dict[str, Any]:
        """Fetch from CCData API."""
        api_key = os.environ.get("CCDATA_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"symbol": "BTC", "limit": 1}

        json_data = await self._get_json(self.CCDATA_API_URL, params=params, headers=headers)

        if not json_data or "data" not in json_data:
            raise ValueError("CCData returned empty response")

        latest = json_data["data"][0] if isinstance(json_data["data"], list) else json_data["data"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": float(latest.get("funding_rate", 0)),
            "btc_oi": float(latest.get("open_interest", 0)),
            "oi_change_1h": float(latest.get("oi_change_1h", 0)),
            "liquidation_spike": bool(latest.get("liquidation_spike", False)),
            "cryptoquant_elr": float(latest.get("elr", 0)),
            "funding_anomaly": abs(float(latest.get("funding_rate", 0))) > 0.01,
            "oi_crash": float(latest.get("oi_change_1h", 0)) < -0.05,
            "leverage_cleanup": False,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock crypto derivatives data."""
        funding = random.uniform(-0.005, 0.01)
        oi_change = random.uniform(-0.1, 0.1)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": round(funding, 6),
            "btc_oi": round(random.uniform(15000, 25000), 2),
            "oi_change_1h": round(oi_change, 4),
            "liquidation_spike": random.random() < 0.1,
            "cryptoquant_elr": round(random.uniform(1.5, 3.5), 2),
            "funding_anomaly": abs(funding) > 0.01,
            "oi_crash": oi_change < -0.05,
            "leverage_cleanup": oi_change < -0.03 and random.random() < 0.5,
        }
