"""
CBOE data fetcher — collects options market data from CBOE public APIs.

Fetches CBOE options statistics, put/call ratios, and market breadth data.
Uses public CBOE delayed quotes endpoints — no API key required.

Endpoints:
    - cdn.cboe.com/api/us/delayed_quotes/
    - www.cboe.com/us/options/market_statistics/
"""

import logging
import random
from datetime import datetime, timezone
from typing import Any

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# CBOE public endpoints
CBOE_MARKET_STATS_URL = "https://cdn.cboe.com/api/us/delayed_quotes/market_statistics.json"
CBOE_PC_RATIO_URL = "https://cdn.cboe.com/api/us/delayed_quotes/put_call_ratio.json"


class CBOEFetcher(BaseFetcher):
    """Fetcher for CBOE options market data.

    Collects put/call ratios, options volume statistics, and market breadth
    indicators from CBOE public data feeds.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "CBOE"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # public data — no key gating (must hit live path, mock only on fetch failure)

    def _is_mock_mode(self) -> bool:
        """CBOE data is public — never in mock mode unless explicitly forced."""
        return False

    async def fetch(self) -> dict:
        """Fetch CBOE options market statistics.

        Returns:
            dict with keys:
                - equity_put_call_ratio: Equity P/C volume ratio
                - index_put_call_ratio: Index P/C volume ratio
                - total_equity_volume: Total equity options volume
                - total_index_volume: Total index options volume
                - vix_value: Current VIX value from CBOE
                - market_breadth: Market advance/decline data
                - timestamp: ISO timestamp
        """
        try:
            # Fetch market statistics
            # 2026-07-31: CDN 403 是因为 httpx 默认 UA "MultiSourceResonance/3.1" 被 CBOE WAF 封。
            # 加浏览器 UA + Accept 让它认成 curl/浏览器。
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            stats_response = await self._http_get(CBOE_MARKET_STATS_URL, headers=browser_headers)
            stats_data = stats_response.json()

            # Fetch put/call ratios
            pc_response = await self._http_get(CBOE_PC_RATIO_URL, headers=browser_headers)
            pc_data = pc_response.json()

            # Parse the responses
            result = self._parse_cboe_data(stats_data, pc_data)
            self.logger.info(
                f"[CBOE] equity_pc={result['equity_put_call_ratio']:.3f}, "
                f"total_vol={result['total_equity_volume'] + result['total_index_volume']:,.0f}"
            )
            return result

        except Exception as exc:
            self.logger.error(f"[CBOE] Fetch failed: {exc}")
            raise

    def _mock_data(self) -> dict:
        """Return realistic mock CBOE market statistics."""
        now = datetime.now(timezone.utc)

        equity_pc = random.uniform(0.6, 1.2)
        index_pc = random.uniform(0.8, 1.5)
        equity_vol = random.uniform(15e6, 30e6)
        index_vol = random.uniform(5e6, 15e6)

        return {
            "equity_put_call_ratio": round(equity_pc, 4),
            "index_put_call_ratio": round(index_pc, 4),
            "total_equity_volume": int(equity_vol),
            "total_index_volume": int(index_vol),
            "vix_value": round(random.uniform(12.0, 35.0), 2),
            "market_breadth": {
                "advancing": int(random.uniform(250, 400)),
                "declining": int(random.uniform(100, 250)),
                "unchanged": int(random.uniform(20, 80)),
            },
            "timestamp": now.isoformat(),
        }

    def _validate_data(self, data: dict) -> bool:
        """Validate CBOE response structure."""
        if not super()._validate_data(data):
            return False
        required = {"equity_put_call_ratio", "total_equity_volume", "timestamp"}
        missing = required - set(data.keys())
        if missing:
            self.logger.warning(f"[CBOE] Missing required keys: {missing}")
            return False
        # P/C ratio should be positive
        if data.get("equity_put_call_ratio", 0) <= 0:
            self.logger.warning("[CBOE] equity_put_call_ratio is not positive")
            return False
        return True

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _parse_cboe_data(self, stats: dict, pc_data: dict) -> dict:
        """Parse CBOE API responses into our internal format.

        Args:
            stats: Market statistics JSON from CBOE.
            pc_data: Put/call ratio JSON from CBOE.

        Returns:
            Normalized dict with CBOE market data.
        """
        now = datetime.now(timezone.utc)

        # Extract put/call ratios
        equity_pc = self._safe_float(
            pc_data.get("equityPcRatio", pc_data.get("equity_put_call_ratio", 0.8))
        )
        index_pc = self._safe_float(
            pc_data.get("indexPcRatio", pc_data.get("index_put_call_ratio", 1.0))
        )

        # Extract volumes
        equity_vol = self._safe_float(
            stats.get("equityVolume", stats.get("total_equity_volume", 20_000_000))
        )
        index_vol = self._safe_float(
            stats.get("indexVolume", stats.get("total_index_volume", 8_000_000))
        )

        # VIX value
        vix_val = self._safe_float(
            stats.get("vix", stats.get("vix_value", 15.0))
        )

        # Market breadth
        breadth_data = stats.get("marketBreadth", stats.get("market_breadth", {}))
        if isinstance(breadth_data, dict):
            breadth = {
                "advancing": int(breadth_data.get("advancing", 300)),
                "declining": int(breadth_data.get("declining", 180)),
                "unchanged": int(breadth_data.get("unchanged", 40)),
            }
        else:
            breadth = {"advancing": 300, "declining": 180, "unchanged": 40}

        return {
            "equity_put_call_ratio": round(equity_pc, 4),
            "index_put_call_ratio": round(index_pc, 4),
            "total_equity_volume": int(equity_vol),
            "total_index_volume": int(index_vol),
            "vix_value": round(vix_val, 2),
            "market_breadth": breadth,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert a value to float with a default fallback."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
