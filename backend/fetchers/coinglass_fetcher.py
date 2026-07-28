"""
Coinglass liquidation and open interest data fetcher.

Fetches crypto liquidation data, open interest, and funding rates
from Coinglass API. Used as supplementary crypto derivatives source.

Source: https://www.coinglass.com/api
Fallback: Returns mock data matching crypto_derivatives model schema.
"""

import os
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base_alt import BaseFetcher


class CoinglassFetcher(BaseFetcher):
    """Fetches Coinglass liquidation and OI data."""

    SOURCE_NAME = "coinglass"
    CONFIG_KEY = "crypto"

    COINGLASS_API_URL = "https://open-api.coinglass.com/public/v2"

    def _check_mock_mode(self) -> bool:
        """Mock mode when Coinglass API key is absent."""
        return not bool(os.environ.get("COINGLASS_API_KEY"))

    async def fetch(self) -> dict[str, Any]:
        """Fetch Coinglass liquidation and OI data."""
        try:
            if self._is_mock:
                data = self._generate_mock_data()
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            data = await self._fetch_coinglass()
            self._record_success()
            return self._build_result(data, extra={"method": "coinglass_api"})
        except Exception as e:
            self.logger.warning(f"Coinglass fetch failed: {e}, returning mock")
            self._record_error(str(e))
            data = self._generate_mock_data()
            return self._build_result(data, extra={"method": "mock_fallback", "error": str(e)})

    async def _fetch_coinglass(self) -> dict[str, Any]:
        """Fetch from Coinglass API."""
        api_key = os.environ.get("COINGLASS_API_KEY", "")
        headers = {"coinglassSecret": api_key}

        # Fetch liquidation data
        liq_url = f"{self.COINGLASS_API_URL}/liquidation"
        liq_data = await self._get_json(liq_url, params={"symbol": "BTC", "time_type": "1"}, headers=headers)

        # Fetch OI data
        oi_url = f"{self.COINGLASS_API_URL}/open-interest"
        oi_data = await self._get_json(oi_url, params={"symbol": "BTC"}, headers=headers)

        # Fetch funding rate
        funding_url = f"{self.COINGLASS_API_URL}/funding"
        funding_data = await self._get_json(funding_url, params={"symbol": "BTC"}, headers=headers)

        # Parse liquidation
        liq_info = liq_data.get("data", {}) if liq_data else {}
        long_liq = float(liq_info.get("longVolUsd", 0))
        short_liq = float(liq_info.get("shortVolUsd", 0))
        liquidation_spike = (long_liq + short_liq) > 100_000_000  # $100M threshold

        # Parse OI
        oi_info = oi_data.get("data", {}) if oi_data else {}
        btc_oi = float(oi_info.get("openInterest", 0))
        oi_change = float(oi_info.get("openInterestChange", 0))

        # Parse funding
        funding_info = funding_data.get("data", {}) if funding_data else {}
        funding_rate = float(funding_info.get("fundingRate", 0))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": round(funding_rate, 6),
            "btc_oi": round(btc_oi, 2),
            "oi_change_1h": round(oi_change, 4),
            "liquidation_spike": liquidation_spike,
            "long_liquidation_usd": round(long_liq, 2),
            "short_liquidation_usd": round(short_liq, 2),
            "cryptoquant_elr": 0.0,  # Not available from Coinglass
            "funding_anomaly": abs(funding_rate) > 0.01,
            "oi_crash": oi_change < -0.05,
            "leverage_cleanup": oi_change < -0.03 and liquidation_spike,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock Coinglass data."""
        funding = random.uniform(-0.005, 0.01)
        oi_change = random.uniform(-0.1, 0.1)
        long_liq = random.uniform(10_000_000, 150_000_000)
        short_liq = random.uniform(10_000_000, 150_000_000)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": round(funding, 6),
            "btc_oi": round(random.uniform(15000, 25000), 2),
            "oi_change_1h": round(oi_change, 4),
            "liquidation_spike": (long_liq + short_liq) > 100_000_000,
            "long_liquidation_usd": round(long_liq, 2),
            "short_liquidation_usd": round(short_liq, 2),
            "cryptoquant_elr": round(random.uniform(1.5, 3.5), 2),
            "funding_anomaly": abs(funding) > 0.01,
            "oi_crash": oi_change < -0.05,
            "leverage_cleanup": oi_change < -0.03 and random.random() < 0.4,
        }
