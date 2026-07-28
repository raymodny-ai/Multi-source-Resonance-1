"""
yfinance data fetcher — collects market OHLCV data using the yfinance library.

Fetches real-time / daily OHLCV (Open, High, Low, Close, Volume) data for
monitored symbols: SPX, SPY, QQQ, IWM, NDX, and VIX.

yfinance is a public library — no API key required.
Endpoint: query1.finance.yahoo.com (via yfinance wrapper)
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# Symbols to track via yfinance
# Note: ^GSPC = SPX, ^NDX = NDX, ^VIX = VIX
YF_TICKER_MAP = {
    "SPX": "^GSPC",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "IWM": "IWM",
    "NDX": "^NDX",
    "VIX": "^VIX",
}


class YFinanceFetcher(BaseFetcher):
    """Fetcher for market OHLCV data via yfinance.

    Collects daily OHLCV bars for all monitored symbols.
    No API key required — uses Yahoo Finance public data.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)
        self._ticker_map = YF_TICKER_MAP

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "yfinance"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # yfinance is public, no key needed

    def _is_mock_mode(self) -> bool:
        """yfinance is public — never in mock mode unless explicitly forced."""
        return False

    async def fetch(self) -> dict:
        """Fetch latest OHLCV data for all tracked symbols.

        Returns:
            dict with keys:
                - prices: dict mapping symbol -> latest OHLCV dict
                - history: dict mapping symbol -> list of recent OHLCV dicts
                - fetch_timestamp: ISO timestamp
        """
        # Import yfinance here to avoid import errors if not installed
        try:
            import yfinance as yf
        except ImportError:
            self.logger.error("[yfinance] yfinance library not installed")
            return self._mock_data()

        now = datetime.now(timezone.utc)
        prices = {}
        history = {}

        for symbol, yf_ticker in self._ticker_map.items():
            try:
                ticker = yf.Ticker(yf_ticker)
                # Get latest daily bar (1 day period)
                hist = ticker.history(period="5d", interval="1d")

                if hist.empty:
                    self.logger.warning(f"[yfinance] No data for {symbol}")
                    continue

                # Latest bar
                latest = hist.iloc[-1]
                prices[symbol] = {
                    "open": round(float(latest["Open"]), 4),
                    "high": round(float(latest["High"]), 4),
                    "low": round(float(latest["Low"]), 4),
                    "close": round(float(latest["Close"]), 4),
                    "volume": int(latest["Volume"]),
                    "timestamp": str(hist.index[-1].date()),
                }

                # Recent history (up to 5 bars)
                history[symbol] = []
                for idx, row in hist.iterrows():
                    history[symbol].append({
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                        "volume": int(row["Volume"]),
                        "timestamp": str(idx.date()),
                    })

                self.logger.info(
                    f"[yfinance] {symbol}: close={prices[symbol]['close']:.2f}, "
                    f"vol={prices[symbol]['volume']:,}"
                )

            except Exception as exc:
                self.logger.error(f"[yfinance] Failed to fetch {symbol}: {exc}")

        return {
            "prices": prices,
            "history": history,
            "fetch_timestamp": now.isoformat(),
            "symbol_count": len(prices),
        }

    def _mock_data(self) -> dict:
        """Return realistic mock OHLCV data for all symbols."""
        now = datetime.now(timezone.utc)

        # Reference prices for mock data
        ref_prices = {
            "SPX": 5750.0, "SPY": 575.0, "QQQ": 510.0,
            "IWM": 225.0, "NDX": 20500.0, "VIX": 15.0,
        }

        prices = {}
        history = {}

        for symbol, ref in ref_prices.items():
            # Add some randomness to the reference price
            close = ref * random.uniform(0.98, 1.02)
            high = close * random.uniform(1.001, 1.015)
            low = close * random.uniform(0.985, 0.999)
            open_price = random.uniform(low, high)
            volume = int(random.uniform(5e6, 8e7))

            prices[symbol] = {
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": volume,
                "timestamp": now.strftime("%Y-%m-%d"),
            }

            # Generate 5 days of mock history
            history[symbol] = []
            base = ref
            for i in range(5):
                day = now - timedelta(days=4 - i)
                day_close = base * random.uniform(0.99, 1.01)
                day_high = day_close * random.uniform(1.001, 1.01)
                day_low = day_close * random.uniform(0.99, 0.999)
                history[symbol].append({
                    "open": round(day_close * random.uniform(0.998, 1.002), 4),
                    "high": round(day_high, 4),
                    "low": round(day_low, 4),
                    "close": round(day_close, 4),
                    "volume": int(random.uniform(5e6, 8e7)),
                    "timestamp": day.strftime("%Y-%m-%d"),
                })
                base = day_close

        return {
            "prices": prices,
            "history": history,
            "fetch_timestamp": now.isoformat(),
            "symbol_count": len(prices),
        }

    def _validate_data(self, data: dict) -> bool:
        """Validate yfinance response structure."""
        if not super()._validate_data(data):
            return False
        if "prices" not in data:
            self.logger.warning("[yfinance] Missing 'prices' key")
            return False
        if not isinstance(data["prices"], dict):
            self.logger.warning("[yfinance] 'prices' is not a dict")
            return False
        # At least one symbol should have data
        if not data["prices"]:
            self.logger.warning("[yfinance] No symbol data returned")
            return False
        return True
