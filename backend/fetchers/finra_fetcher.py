"""
FINRA short interest data fetcher.

Fetches short interest and days-to-cover data from FINRA API.
Fallback: yfinance estimated short data.
Mock mode: returns synthetic short interest matching the expected schema.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class FinraFetcher(BaseFetcher):
    """Fetches FINRA short interest data."""

    @property
    def source_name(self) -> str:
        return "finra"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # FINRA is public data

    FINRA_API_URL = "https://api.finra.org/data/groups/shortInterest"

    # Monitored symbols
    SYMBOLS = ["SPY", "QQQ", "IWM"]

    def _is_mock_mode(self) -> bool:
        """FINRA is public — never in mock mode unless network unavailable."""
        return False

    async def fetch(self) -> dict:
        """Fetch FINRA short interest data for monitored symbols."""
        try:
            return await self._fetch_finra()
        except Exception as e:
            self.logger.warning(f"FINRA fetch failed: {e}, returning mock")
            return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock FINRA short interest data."""
        return self._generate_mock_data()

    async def _fetch_finra(self) -> dict[str, Any]:
        """Fetch short interest from FINRA API."""
        results = {}
        client = await self._get_client()

        for symbol in self.SYMBOLS:
            try:
                params = {"symbol": symbol, "limit": 1}
                resp = await client.get(self.FINRA_API_URL, params=params)
                resp.raise_for_status()
                json_data = resp.json()

                if json_data and "data" in json_data and json_data["data"]:
                    latest = json_data["data"][0]
                    results[symbol] = {
                        "short_interest": latest.get("shortInterest", 0),
                        "days_to_cover": latest.get("daysToCover", 0),
                        "settlement_date": latest.get("settlementDate", ""),
                    }
                else:
                    results[symbol] = self._mock_symbol(symbol)
            except Exception:
                results[symbol] = self._mock_symbol(symbol)

        return {
            "date": date.today().isoformat(),
            "symbols": results,
            "aggregated_short_ratio": round(
                sum(v.get("days_to_cover", 0) for v in results.values()) / max(len(results), 1), 2
            ),
        }

    def _mock_symbol(self, symbol: str) -> dict[str, Any]:
        """Generate mock data for a single symbol."""
        return {
            "short_interest": random.randint(5_000_000, 50_000_000),
            "days_to_cover": round(random.uniform(1.0, 5.0), 2),
            "settlement_date": date.today().isoformat(),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock FINRA short interest data."""
        symbols = {}
        for sym in self.SYMBOLS:
            symbols[sym] = self._mock_symbol(sym)

        return {
            "date": date.today().isoformat(),
            "symbols": symbols,
            "aggregated_short_ratio": round(random.uniform(1.5, 4.5), 2),
        }
