"""
Tradier option chain data fetcher.

Fetches option chain data from Tradier API for GEX calculation
and put-call ratio analysis. Requires TRADIER_API_KEY.

Source: https://api.tradier.com/v1/
Fallback: Returns mock data matching expected schema.
"""

import os
import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base_alt import BaseFetcher


class TradierFetcher(BaseFetcher):
    """Fetches Tradier option chain data."""

    SOURCE_NAME = "tradier"
    CONFIG_KEY = ""  # Requires TRADIER_API_KEY env var

    TRADIER_API_URL = "https://api.tradier.com/v1/markets/options"
    TRADIER_CHAIN_URL = "https://api.tradier.com/v1/markets/options/chains"

    # Symbols to fetch option chains for
    SYMBOLS = ["SPY", "QQQ", "IWM"]

    def _check_mock_mode(self) -> bool:
        """Mock mode when Tradier API key is absent."""
        return not bool(os.environ.get("TRADIER_API_KEY"))

    async def fetch(self) -> dict[str, Any]:
        """Fetch Tradier option chain data."""
        try:
            if self._is_mock:
                data = self._generate_mock_data()
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            data = await self._fetch_tradier()
            self._record_success()
            return self._build_result(data, extra={"method": "tradier_api"})
        except Exception as e:
            self.logger.warning(f"Tradier fetch failed: {e}, returning mock")
            self._record_error(str(e))
            data = self._generate_mock_data()
            return self._build_result(data, extra={"method": "mock_fallback", "error": str(e)})

    async def _fetch_tradier(self) -> dict[str, Any]:
        """Fetch option chains from Tradier API."""
        api_key = os.environ.get("TRADIER_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        results = {}
        for symbol in self.SYMBOLS:
            try:
                params = {"symbol": symbol, "greeks": True}
                json_data = await self._get_json(self.TRADIER_CHAIN_URL, params=params, headers=headers)

                if json_data and "options" in json_data and "option" in json_data["options"]:
                    options = json_data["options"]["option"]
                    calls = [o for o in options if o.get("option_type") == "call"]
                    puts = [o for o in options if o.get("option_type") == "put"]

                    total_call_oi = sum(o.get("open_interest", 0) for o in calls)
                    total_put_oi = sum(o.get("open_interest", 0) for o in puts)
                    pc_ratio = total_put_oi / max(total_call_oi, 1)

                    results[symbol] = {
                        "call_oi": total_call_oi,
                        "put_oi": total_put_oi,
                        "put_call_ratio": round(pc_ratio, 4),
                        "total_options": len(options),
                        "nearest_expiry": options[0].get("expiration_date", "") if options else "",
                    }
                else:
                    results[symbol] = self._mock_symbol(symbol)
            except Exception:
                results[symbol] = self._mock_symbol(symbol)

        # Aggregate
        total_calls = sum(v.get("call_oi", 0) for v in results.values())
        total_puts = sum(v.get("put_oi", 0) for v in results.values())

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": results,
            "aggregate_put_call_ratio": round(total_puts / max(total_calls, 1), 4),
            "total_call_oi": total_calls,
            "total_put_oi": total_puts,
        }

    def _mock_symbol(self, symbol: str) -> dict[str, Any]:
        """Generate mock data for a single symbol."""
        call_oi = random.randint(500_000, 2_000_000)
        put_oi = random.randint(400_000, 1_800_000)
        return {
            "call_oi": call_oi,
            "put_oi": put_oi,
            "put_call_ratio": round(put_oi / max(call_oi, 1), 4),
            "total_options": random.randint(500, 2000),
            "nearest_expiry": date.today().isoformat(),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock Tradier option chain data."""
        symbols = {sym: self._mock_symbol(sym) for sym in self.SYMBOLS}
        total_calls = sum(v["call_oi"] for v in symbols.values())
        total_puts = sum(v["put_oi"] for v in symbols.values())

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": symbols,
            "aggregate_put_call_ratio": round(total_puts / max(total_calls, 1), 4),
            "total_call_oi": total_calls,
            "total_put_oi": total_puts,
        }
