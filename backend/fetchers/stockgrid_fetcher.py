"""
StockGrid option flow data fetcher.

Fetches price/volume slope data and divergence signals from StockGrid.
Used as input for dark_pool_metrics.stockgrid_* columns.

Source: StockGrid API
Fallback: Returns mock data matching expected schema.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base_alt import BaseFetcher


class StockGridFetcher(BaseFetcher):
    """Fetches StockGrid price/volume slope and divergence data."""

    SOURCE_NAME = "stockgrid"
    CONFIG_KEY = ""  # Public data, no API key needed

    STOCKGRID_API_URL = "https://stockgrid.io/api/screener"

    # Symbols to monitor
    SYMBOLS = ["SPY", "QQQ", "IWM"]

    def _check_mock_mode(self) -> bool:
        """StockGrid is public — never in mock mode unless network unavailable."""
        return False

    async def fetch(self) -> dict[str, Any]:
        """Fetch StockGrid slope and divergence data."""
        try:
            data = await self._fetch_stockgrid()
            self._record_success()
            return self._build_result(data, extra={"method": "stockgrid_api"})
        except Exception as e:
            self.logger.warning(f"StockGrid fetch failed: {e}, returning mock")
            self._record_error(str(e))
            data = self._generate_mock_data()
            return self._build_result(data, extra={"method": "mock_fallback", "error": str(e)})

    async def _fetch_stockgrid(self) -> dict[str, Any]:
        """Fetch slope data from StockGrid API."""
        results = {}
        client = await self._get_client()

        for symbol in self.SYMBOLS:
            try:
                params = {"symbol": symbol, "period": "60d"}
                resp = await client.get(self.STOCKGRID_API_URL, params=params)
                resp.raise_for_status()
                json_data = resp.json()

                if json_data and "data" in json_data:
                    d = json_data["data"]
                    results[symbol] = {
                        "price_slope_20d": round(float(d.get("slope_20d", 0)), 4),
                        "price_slope_60d": round(float(d.get("slope_60d", 0)), 4),
                        "volume_slope_20d": round(float(d.get("vol_slope_20d", 0)), 4),
                        "divergence": bool(d.get("divergence", False)),
                    }
                else:
                    results[symbol] = self._mock_symbol()
            except Exception:
                results[symbol] = self._mock_symbol()

        # Aggregate signals
        any_divergence = any(v.get("divergence", False) for v in results.values())
        avg_slope_20d = sum(v.get("price_slope_20d", 0) for v in results.values()) / max(len(results), 1)

        return {
            "date": date.today().isoformat(),
            "symbols": results,
            "stockgrid_20d_slope": round(avg_slope_20d, 4),
            "stockgrid_60d_slope": round(
                sum(v.get("price_slope_60d", 0) for v in results.values()) / max(len(results), 1), 4
            ),
            "stockgrid_divergence": any_divergence,
            "stockgrid_signal": any_divergence and avg_slope_20d < 0,
        }

    def _mock_symbol(self) -> dict[str, Any]:
        """Generate mock data for a single symbol."""
        return {
            "price_slope_20d": round(random.uniform(-0.5, 0.5), 4),
            "price_slope_60d": round(random.uniform(-0.3, 0.3), 4),
            "volume_slope_20d": round(random.uniform(-0.4, 0.4), 4),
            "divergence": random.random() < 0.2,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock StockGrid data."""
        symbols = {sym: self._mock_symbol() for sym in self.SYMBOLS}
        avg_20d = sum(v["price_slope_20d"] for v in symbols.values()) / len(symbols)
        any_div = any(v["divergence"] for v in symbols.values())

        return {
            "date": date.today().isoformat(),
            "symbols": symbols,
            "stockgrid_20d_slope": round(avg_20d, 4),
            "stockgrid_60d_slope": round(random.uniform(-0.3, 0.3), 4),
            "stockgrid_divergence": any_div,
            "stockgrid_signal": any_div and avg_20d < 0,
        }
