"""
Money flow data fetcher.

Collects money flow indicators: net buying/selling pressure,
institutional flow metrics, and dark pool net volume.
Always runs in mock mode (no dedicated free API).
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class FlowFetcher(BaseFetcher):
    """Fetches money flow data: institutional buying/selling pressure."""

    @property
    def source_name(self) -> str:
        return "money_flow"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # Always mock

    async def fetch(self) -> dict:
        """Fetch money flow data."""
        return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock money flow data."""
        return self._generate_mock_data()

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock money flow data."""
        net_flow = random.uniform(-2000, 2000)
        institutional_flow = random.uniform(-1500, 1500)
        retail_flow = net_flow - institutional_flow

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "net_money_flow": round(net_flow, 2),
            "institutional_flow": round(institutional_flow, 2),
            "retail_flow": round(retail_flow, 2),
            "dark_pool_net_volume": round(random.uniform(-800, 800), 2),
            "block_trade_volume": round(random.uniform(50, 500), 2),
            "flow_direction": "inflow" if net_flow > 0 else "outflow",
            "flow_strength": abs(net_flow) / 2000,  # Normalised 0-1
            "consecutive_inflow_days": random.randint(0, 8),
            "is_accumulation": net_flow > 500,
        }
