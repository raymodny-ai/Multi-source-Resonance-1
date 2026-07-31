"""
DBMF moving average data fetcher.

Fetches DBMF ETF value and moving average data for recovery signals.
Used as input for dark_pool_metrics.dbmf_ma5_recovery column.

Source: DBMF ETF public data / Yahoo Finance
Fallback: Returns mock data matching expected schema.
"""

import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class DBMFFetcher(BaseFetcher):
    """Fetches DBMF moving average data for recovery detection."""

    @property
    def source_name(self) -> str:
        return "dbmf"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # Public data, no API key needed

    # DBMF ticker on Yahoo Finance
    DBMF_SYMBOL = "DBMF"

    def _is_mock_mode(self) -> bool:
        """DBMF is public — never in mock mode unless network unavailable."""
        return False

    async def fetch(self) -> dict:
        """Fetch DBMF value and moving average data."""
        try:
            return await self._fetch_dbmf()
        except Exception as e:
            self.logger.warning(f"DBMF fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock DBMF data."""
        return self._generate_mock_data()

    async def _fetch_dbmf(self) -> dict[str, Any]:
        """Fetch DBMF data via yfinance or direct API."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(self.DBMF_SYMBOL)
            hist = ticker.history(period="30d")

            if hist.empty or len(hist) < 5:
                raise ValueError("Insufficient DBMF history data")

            closes = hist["Close"].dropna()
            current_value = float(closes.iloc[-1])

            # Calculate moving averages
            ma5 = float(closes.tail(5).mean())
            ma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else float(closes.mean())

            # Recovery signal: price crossed above MA5
            prev_close = float(closes.iloc[-2]) if len(closes) > 1 else current_value
            ma5_recovery = prev_close < ma5 and current_value >= ma5

            # Trend
            above_ma5 = current_value > ma5
            above_ma20 = current_value > ma20

            return {
                "date": date.today().isoformat(),
                "dbmf_value": round(current_value, 4),
                "ma5": round(ma5, 4),
                "ma20": round(ma20, 4),
                "ma5_recovery": ma5_recovery,
                "above_ma5": above_ma5,
                "above_ma20": above_ma20,
                "dbmf_ma5_recovery": ma5_recovery,  # Alias for dark_pool_metrics column
                "daily_change_pct": round(
                    ((current_value - prev_close) / max(prev_close, 0.01)) * 100, 2
                ),
            }
        except ImportError:
            # yfinance not available, use HTTP fallback
            return await self._fetch_via_http()

    async def _fetch_via_http(self) -> dict[str, Any]:
        """Fallback: fetch DBMF data via direct HTTP."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.DBMF_SYMBOL}"
        params = {"range": "1mo", "interval": "1d"}

        json_data = await self._get_json(url, params=params)

        if not json_data or "chart" not in json_data:
            raise ValueError("Yahoo Finance returned empty response")

        result = json_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]

        if len(closes) < 5:
            raise ValueError("Insufficient DBMF price data")

        current = closes[-1]
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / min(len(closes), 20)
        prev = closes[-2] if len(closes) > 1 else current

        return {
            "date": date.today().isoformat(),
            "dbmf_value": round(current, 4),
            "ma5": round(ma5, 4),
            "ma20": round(ma20, 4),
            "ma5_recovery": prev < ma5 and current >= ma5,
            "above_ma5": current > ma5,
            "above_ma20": current > ma20,
            "dbmf_ma5_recovery": prev < ma5 and current >= ma5,
            "daily_change_pct": round(((current - prev) / max(prev, 0.01)) * 100, 2),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock DBMF data."""
        value = round(random.uniform(20.0, 35.0), 4)
        ma5 = round(value + random.uniform(-0.5, 0.5), 4)
        ma20 = round(value + random.uniform(-1.0, 1.0), 4)
        prev = round(value - random.uniform(-0.3, 0.3), 4)

        ma5_recovery = prev < ma5 and value >= ma5

        return {
            "date": date.today().isoformat(),
            "dbmf_value": value,
            "ma5": ma5,
            "ma20": ma20,
            "ma5_recovery": ma5_recovery,
            "above_ma5": value > ma5,
            "above_ma20": value > ma20,
            "dbmf_ma5_recovery": ma5_recovery,
            "daily_change_pct": round(random.uniform(-2.0, 2.0), 2),
        }
