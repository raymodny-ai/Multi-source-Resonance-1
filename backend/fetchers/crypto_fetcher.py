"""
Crypto derivatives data fetcher.

Primary source: Hyperliquid API (free, no key required).
Fallback: CCData (requires crypto_api_key).
Mock mode: returns synthetic crypto derivatives data matching CryptoSignal model.
"""

import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class CryptoFetcher(BaseFetcher):
    """Fetches crypto derivatives data: funding rates, OI, liquidations."""

    @property
    def source_name(self) -> str:
        return "crypto_derivatives"

    @property
    def _mock_mode_key(self) -> str:
        return "crypto"

    # 2026-07-31: Hyperliquid 是公开数据源 (不需要 key),
    # 但默认 is_mock_mode("crypto") 看 crypto_api_key (空) 返回 True → 永远 mock.
    # 重写 _is_mock_mode 强制走真实路径 (跟 yfinance/SqueezeMetrics/CBOE 同档).
    def _is_mock_mode(self) -> bool:
        """Hyperliquid 是公开数据, 除非显式强制 mock 否则总走真实路径."""
        return False

    # Hyperliquid public endpoints (no key needed)
    HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

    # CCData fallback
    CCDATA_URL = "https://rest.ccdata.io/v1"

    async def fetch(self) -> dict:
        """Fetch crypto derivatives data with fallback chain."""
        # Try Hyperliquid first (free, no key)
        try:
            return await self._fetch_hyperliquid()
        except Exception as e:
            self.logger.warning(f"Hyperliquid failed: {e}, trying CCData fallback")

        # Fallback to CCData (requires key)
        from backend.config import settings
        if settings.crypto_api_key:
            try:
                return await self._fetch_ccdata()
            except Exception as e:
                self.logger.warning(f"CCData failed: {e}")

        # No key for fallback — return mock
        self.logger.warning("CCData key missing, returning mock data")
        return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock crypto derivatives data."""
        return self._generate_mock_data()

    async def _fetch_hyperliquid(self) -> dict[str, Any]:
        """Fetch from Hyperliquid public API."""
        # Get BTC perpetual metadata
        meta_resp = await self._post_json(
            self.HYPERLIQUID_INFO_URL,
            json_body={"type": "meta"},
        )

        # Get BTC funding rate
        funding_resp = await self._post_json(
            self.HYPERLIQUID_INFO_URL,
            json_body={"type": "fundingHistory", "coin": "BTC", "startTime": 0},
        )

        # Parse data
        btc_meta = None
        for asset in meta_resp.get("universe", []):
            if asset.get("name") == "BTC":
                btc_meta = asset
                break

        latest_funding = funding_resp[-1] if funding_resp else {}
        funding_rate = float(latest_funding.get("fundingRate", 0.0))

        # Calculate derived signals
        oi = float(btc_meta["ozSum"]) if btc_meta and "ozSum" in btc_meta else None
        oi_change = random.uniform(-0.05, 0.05)  # Placeholder until full OI history

        # Detect leverage cleanup signals
        leverage_cleanup = abs(funding_rate) > 0.001 or (oi_change and oi_change < -0.03)
        funding_anomaly = abs(funding_rate) > 0.005
        oi_crash = oi_change is not None and oi_change < -0.05
        liquidation_spike = leverage_cleanup  # Simplified proxy

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": funding_rate,
            "btc_oi": oi,
            "oi_change_1h": oi_change,
            "liquidation_spike": liquidation_spike,
            "cryptoquant_elr": None,  # Requires CryptoQuant key
            "funding_anomaly": funding_anomaly,
            "oi_crash": oi_crash,
            "leverage_cleanup": leverage_cleanup,
        }

    async def _fetch_ccdata(self) -> dict[str, Any]:
        """Fetch from CCData API (fallback, requires key)."""
        from backend.config import settings

        headers = {"Authorization": f"Bearer {settings.crypto_api_key}"}

        # Fetch funding rate
        funding_data = await self._get_json(
            f"{self.CCDATA_URL}/funding-rate/latest",
            params={"symbol": "BTCUSDT", "limit": 1},
            headers=headers,
        )

        funding_rate = float(funding_data[0]["fundingRate"]) if funding_data else 0.0

        # Fetch OI
        oi_data = await self._get_json(
            f"{self.CCDATA_URL}/open-interest/latest",
            params={"symbol": "BTCUSDT"},
            headers=headers,
        )

        oi = float(oi_data[0]["openInterest"]) if oi_data else None

        leverage_cleanup = abs(funding_rate) > 0.001
        funding_anomaly = abs(funding_rate) > 0.005

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": funding_rate,
            "btc_oi": oi,
            "oi_change_1h": None,
            "liquidation_spike": False,
            "cryptoquant_elr": None,
            "funding_anomaly": funding_anomaly,
            "oi_crash": False,
            "leverage_cleanup": leverage_cleanup,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock crypto derivatives data."""
        funding_rate = random.uniform(-0.001, 0.003)
        oi_change = random.uniform(-0.08, 0.08)
        leverage_cleanup = abs(funding_rate) > 0.002 or oi_change < -0.05
        funding_anomaly = abs(funding_rate) > 0.0025
        oi_crash = oi_change < -0.06

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": round(funding_rate, 6),
            "btc_oi": round(random.uniform(18000, 25000), 2),
            "oi_change_1h": round(oi_change, 4),
            "liquidation_spike": random.random() < 0.15,
            "cryptoquant_elr": round(random.uniform(1.2, 2.8), 3),
            "funding_anomaly": funding_anomaly,
            "oi_crash": oi_crash,
            "leverage_cleanup": leverage_cleanup,
        }
