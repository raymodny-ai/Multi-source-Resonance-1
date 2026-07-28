"""
Sector rotation data fetcher.

Collects sector performance data: relative strength of S&P 500 sectors,
rotation signals, defensive vs cyclical leadership.
Always runs in mock mode (no dedicated free API for sector rotation).
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


# S&P 500 sector ETFs
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

# Defensive sectors (risk-off leadership)
DEFENSIVE_SECTORS = {"XLU", "XLP", "XLV"}
CYCLICAL_SECTORS = {"XLE", "XLI", "XLY", "XLB", "XLK", "XLF"}


class SectorFetcher(BaseFetcher):
    """Fetches sector rotation and relative performance data."""

    @property
    def source_name(self) -> str:
        return "sector_rotation"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # Always mock

    async def fetch(self) -> dict:
        """Fetch sector rotation data."""
        return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock sector rotation data."""
        return self._generate_mock_data()

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock sector rotation data."""
        # Generate random performance for each sector
        sector_perf = {}
        for etf, name in SECTOR_ETFS.items():
            sector_perf[etf] = {
                "name": name,
                "daily_return": round(random.uniform(-3.0, 3.0), 2),
                "weekly_return": round(random.uniform(-5.0, 5.0), 2),
                "monthly_return": round(random.uniform(-8.0, 8.0), 2),
            }

        # Determine leadership
        best_sector = max(sector_perf.items(), key=lambda x: x[1]["daily_return"])
        worst_sector = min(sector_perf.items(), key=lambda x: x[1]["daily_return"])

        # Compute defensive vs cyclical average
        defensive_avg = sum(
            sector_perf[s]["daily_return"] for s in DEFENSIVE_SECTORS if s in sector_perf
        ) / len(DEFENSIVE_SECTORS)
        cyclical_avg = sum(
            sector_perf[s]["daily_return"] for s in CYCLICAL_SECTORS if s in sector_perf
        ) / len(CYCLICAL_SECTORS)

        # Rotation signal
        if defensive_avg > cyclical_avg + 1.0:
            rotation_signal = "risk_off"
        elif cyclical_avg > defensive_avg + 1.0:
            rotation_signal = "risk_on"
        else:
            rotation_signal = "neutral"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sector_performance": sector_perf,
            "best_sector": {"etf": best_sector[0], "return": best_sector[1]["daily_return"]},
            "worst_sector": {"etf": worst_sector[0], "return": worst_sector[1]["daily_return"]},
            "defensive_avg_return": round(defensive_avg, 2),
            "cyclical_avg_return": round(cyclical_avg, 2),
            "rotation_signal": rotation_signal,
            "breadth_positive": sum(1 for s in sector_perf.values() if s["daily_return"] > 0) > 5,
        }
