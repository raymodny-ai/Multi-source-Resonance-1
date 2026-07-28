"""
AXLFI data fetcher — collects dark pool net position data from AXLFI API.

AXLFI provides AI-driven cross-asset signals including dark pool net positions,
dark volume, and institutional flow metrics. This data feeds the darkpool_score
dimension of the resonance scoring system.

Typical latency: ~9.32s (can be backgrounded / delayed write)
"""

import logging
import random
from datetime import datetime, timezone
from typing import Any

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# AXLFI API endpoint
AXLFI_BASE_URL = "https://api.axlfi.com/v1"


class AXLFIFetcher(BaseFetcher):
    """Fetcher for AXLFI dark pool net position and cross-asset signals.

    Collects daily dark pool net positions, dark volume, and related metrics
    that feed into the darkpool dimension of the resonance scoring system.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "AXLFI"

    @property
    def _mock_mode_key(self) -> str:
        return "axlfi"

    async def fetch(self) -> dict:
        """Fetch AXLFI dark pool data.

        Returns:
            dict with keys:
                - dark_net_position: Net dark pool position (float)
                - dark_volume: Dark pool volume (float)
                - dark_buy_ratio: Ratio of dark buys to total (float, 0-1)
                - institutional_flow: Institutional flow indicator (float)
                - timestamp: ISO timestamp
        """
        url = f"{AXLFI_BASE_URL}/darkpool/signals"
        headers = {}
        if self.config.axlfi_api_key:
            headers["Authorization"] = f"Bearer {self.config.axlfi_api_key}"
            headers["X-API-Key"] = self.config.axlfi_api_key

        response = await self._http_get(url, headers=headers)
        data = response.json()

        # Normalize the response to our internal format
        result = {
            "dark_net_position": float(data.get("dark_net_position", data.get("net_position", 0))),
            "dark_volume": float(data.get("dark_volume", data.get("volume", 0))),
            "dark_buy_ratio": float(data.get("dark_buy_ratio", data.get("buy_ratio", 0.5))),
            "institutional_flow": float(data.get("institutional_flow", data.get("inst_flow", 0))),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "symbols": data.get("symbols", ["SPY", "QQQ", "IWM"]),
        }

        self.logger.info(
            f"[AXLFI] dark_net_position={result['dark_net_position']:.2f}, "
            f"dark_volume={result['dark_volume']:.0f}"
        )

        return result

    def _mock_data(self) -> dict:
        """Return realistic mock AXLFI dark pool data."""
        now = datetime.now(timezone.utc)
        dark_net = random.gauss(-500_000_000, 200_000_000)  # Typically negative
        dark_vol = random.uniform(5e9, 15e9)
        buy_ratio = random.uniform(0.35, 0.55)

        return {
            "dark_net_position": round(dark_net, 2),
            "dark_volume": round(dark_vol, 2),
            "dark_buy_ratio": round(buy_ratio, 4),
            "institutional_flow": round(random.gauss(0, 1e8), 2),
            "timestamp": now.isoformat(),
            "symbols": ["SPY", "QQQ", "IWM"],
        }

    def _validate_data(self, data: dict) -> bool:
        """Validate AXLFI response structure."""
        if not super()._validate_data(data):
            return False
        required_keys = {"dark_net_position", "dark_volume", "timestamp"}
        missing = required_keys - set(data.keys())
        if missing:
            self.logger.warning(f"[AXLFI] Missing required keys: {missing}")
            return False
        return True
