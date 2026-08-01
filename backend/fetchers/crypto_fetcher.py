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
            result = await self._fetch_hyperliquid()
        except Exception as e:
            self.logger.warning(f"Hyperliquid failed: {e}, trying CCData fallback")
            result = None

        if result is None:
            # Fallback to CCData (requires key)
            from backend.config import settings
            if settings.crypto_api_key:
                try:
                    result = await self._fetch_ccdata()
                except Exception as e:
                    self.logger.warning(f"CCData failed: {e}")

        # Enrich with CoinGecko free market prices (BTC/ETH spot + 24h change/volume)
        if result is not None:
            try:
                cg = await self._fetch_coingecko()
                if cg:
                    result.update(cg)
            except Exception as e:
                self.logger.warning(f"CoinGecko enrichment failed: {e}")
            # Compute ELR proxy from real data once both OI and volume are known.
            # Uses the key-free positioning-intensity ratio:
            #   ELR ≈ notional open interest / hourly spot volume
            #     = (btc_oi × btc_mark) / (btc_volume_24h / 24)
            # This is an OI-based leverage proxy (a true CryptoQuant ELR needs a
            # paid key + exchange BTC reserves, which Hyperliquid does not expose
            # via its free API). Formula origin: 2026-08-02, msn proxy B.
            self._compute_elr_proxy(result)
            return result

        # No source returned usable data — return mock
        self.logger.warning("CCData key missing, returning mock data")
        mock = self._generate_mock_data()
        mock["_internal_mock"] = True
        return mock

    def _mock_data(self) -> dict:
        """Return mock crypto derivatives data."""
        return self._generate_mock_data()

    async def _fetch_hyperliquid(self) -> dict[str, Any]:
        """Fetch from Hyperliquid public API.

        Uses `metaAndAssetCtxs` (single call) to get BTC open interest,
        mark price, and funding — all in one request. Previously used the
        `meta` endpoint + `ozSum`, but that field does not exist there, so
        btc_oi was always null (2026-08-02 fix).
        """
        ctx = await self._post_json(
            self.HYPERLIQUID_INFO_URL,
            json_body={"type": "metaAndAssetCtxs"},
        )

        # ctx = [universe, asset_ctxs] (parallel arrays)
        universe = ctx[0].get("universe", [])
        asset_ctxs = ctx[1] if len(ctx) > 1 else []

        btc_ctx = None
        for i, asset in enumerate(universe):
            if asset.get("name") == "BTC" and i < len(asset_ctxs):
                btc_ctx = asset_ctxs[i]
                break

        if btc_ctx is None:
            raise ValueError("BTC context not found in Hyperliquid metaAndAssetCtxs")

        funding_rate = float(btc_ctx.get("funding", 0.0))
        oi = float(btc_ctx.get("openInterest"))
        mark = float(btc_ctx.get("markPx", 0.0))

        # FIX-13 note: oi_change_1h is not produced here — the DataWriter
        # computes it from the crypto_oi_history snapshot table. The fetcher
        # stays stateless. (2026-08-02: writer now fills it with real values.)
        leverage_cleanup = abs(funding_rate) > 0.001
        funding_anomaly = abs(funding_rate) > 0.005

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_funding_rate": funding_rate,
            "btc_oi": oi,
            "btc_mark": mark,
            "oi_change_1h": None,  # computed by writer from snapshot history
            "liquidation_spike": False,
            "cryptoquant_elr": None,  # computed in fetch() after volume known
            "funding_anomaly": funding_anomaly,
            "oi_crash": False,
            "leverage_cleanup": leverage_cleanup,
        }

    def _compute_elr_proxy(self, data: dict) -> None:
        """Fill cryptoquant_elr with the key-free OI-based leverage proxy.

        Mutates ``data`` in place. Leaves ``cryptoquant_elr`` as None if the
        inputs are unavailable (OI / mark / volume missing).
        Formula (2026-08-02 proxy B):
            ELR ≈ notional open interest / hourly spot volume
              = (btc_oi × btc_mark) / (btc_volume_24h / 24)
        A true CryptoQuant ELR needs a paid key + exchange BTC reserves which
        Hyperliquid's free API does not expose; this is a real, key-free
        positioning-intensity proxy landing in the same magnitude.
        """
        oi = data.get("btc_oi")
        mark = data.get("btc_mark")
        vol24 = data.get("btc_volume")
        if oi is None or mark is None or not vol24 or vol24 <= 0:
            data["cryptoquant_elr"] = None
            return
        hourly_vol = vol24 / 24.0
        notional_usd = oi * mark
        data["cryptoquant_elr"] = round(notional_usd / hourly_vol, 3)
        # btc_mark is kept in the dict (not a crypto_derivatives column) so the
        # writer can persist it into crypto_oi_history for future leverage uses.

    # CoinGecko free public API (no key required) — enriched market prices.
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

    async def _fetch_coingecko(self) -> dict[str, Any]:
        """Enrich with BTC/ETH spot prices from CoinGecko free API.

        Returns empty dict on any failure (enrichment is best-effort; the
        underlying derivatives data is still returned by the caller).
        """
        resp = await self._http_get(
            f"{self.COINGECKO_URL}"
            "?ids=bitcoin,ethereum&vs_currencies=usd"
            "&include_24hr_change=true&include_24hr_vol=true",
            headers={"accept": "application/json"},
        )
        data = resp.json()
        btc = data.get("bitcoin") or {}
        eth = data.get("ethereum") or {}
        if btc.get("usd") is None:
            return {}
        return {
            "btc_price": btc.get("usd"),
            "btc_24h_change": btc.get("usd_24h_change"),
            "btc_volume": btc.get("usd_24h_vol"),
            "eth_price": eth.get("usd"),
            "eth_24h_change": eth.get("usd_24h_change"),
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
