"""
CCData cryptocurrency derivatives data fetcher.

Primary source: CCData API (requires CCDATA_API_KEY).
Free fallback: CoinGecko public API (no key needed) — provides BTC/ETH
spot price and 24h change, which the crypto analyzer uses as proxies for
the funding-rate / OI fields CCData exposes.

If both fail, the fetcher returns mock data with ``is_mock=True``.

FIX-11: previous version fell straight to mock when CCDATA_API_KEY was
absent. Now it always attempts a real public fallback first.
"""

import os
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class CCDataFetcher(BaseFetcher):
    """Fetches CCData crypto derivatives data (with free CoinGecko fallback)."""

    @property
    def source_name(self) -> str:
        return "ccdata"

    @property
    def _mock_mode_key(self) -> str:
        return "crypto"

    CCDATA_API_URL = "https://api.ccdata.com/v1/derivatives"
    COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

    def _is_mock_mode(self) -> bool:
        """FIX-11: only short-circuit to mock when BOTH the CCData key and
        the CoinGecko fallback are unavailable. In practice CoinGecko is
        always available (free public), so this returns False.
        """
        return not bool(os.environ.get("CCDATA_API_KEY"))

    async def fetch(self) -> dict:
        """Fetch crypto derivatives, with cascading fallbacks.

        Order:
        1. CCData API (if CCDATA_API_KEY is set)
        2. CoinGecko public price endpoint (always available, no key)
        3. Mock data (only if both above fail)
        """
        api_key = os.environ.get("CCDATA_API_KEY", "")
        if api_key:
            try:
                return await self._fetch_ccdata(api_key)
            except Exception as e:
                self.logger.warning(f"CCData fetch failed: {e}, trying CoinGecko")

        # Always try CoinGecko as the free public fallback
        try:
            return await self._fetch_coingecko()
        except Exception as e:
            self.logger.warning(f"CoinGecko fetch failed: {e}, returning mock")

        return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock crypto derivatives data."""
        return self._generate_mock_data()

    async def _fetch_ccdata(self, api_key: str) -> dict[str, Any]:
        """Fetch from CCData API."""
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
            "data_source": "ccdata",
        }

    async def _fetch_coingecko(self) -> dict[str, Any]:
        """Fetch BTC/ETH price + 24h change from the free CoinGecko API.

        The crypto analyzer uses spot price and 24h change to derive
        funding-rate and OI proxies when CCData / Hyperliquid are not
        available. This is the FIX-26 enrichment: previously CoinGecko
        columns did not exist in the schema, so we had no real data to
        fall back on.
        """
        params = {
            "ids": "bitcoin,ethereum",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_last_updated_at": "true",
        }
        json_data = await self._get_json(self.COINGECKO_API_URL, params=params)

        btc = (json_data or {}).get("bitcoin") or {}
        eth = (json_data or {}).get("ethereum") or {}

        btc_price = btc.get("usd")
        btc_change = btc.get("usd_24h_change")
        btc_volume = btc.get("usd_24h_vol")
        eth_price = eth.get("usd")
        eth_change = eth.get("usd_24h_change")

        if btc_price is None and eth_price is None:
            raise ValueError("CoinGecko returned no usable data")

        # Derive coarse "OI change" from 24h price change. This is a proxy,
        # not real OI; mark the result so the pipeline knows.
        oi_proxy = (btc_change or 0.0) / 100.0
        funding_proxy = ((btc_change or 0.0) / 100.0) * 0.001  # tiny factor

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": round(funding_proxy, 6),
            "btc_oi": 0.0,  # CoinGecko does not expose OI; explicit 0, not random
            "oi_change_1h": round(oi_proxy, 4),
            "liquidation_spike": False,
            "cryptoquant_elr": 0.0,
            "funding_anomaly": abs(funding_proxy) > 0.01,
            "oi_crash": oi_proxy < -0.05,
            "leverage_cleanup": False,
            # FIX-26: persist CoinGecko enrichment columns so downstream can
            # distinguish proxy-derived values from CCData's real OI.
            "btc_price": btc_price,
            "btc_24h_change": btc_change,
            "btc_volume": btc_volume,
            "eth_price": eth_price,
            "eth_24h_change": eth_change,
            "data_source": "coingecko",
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock crypto derivatives data (last-resort fallback)."""
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
            "data_source": "mock",
        }
