"""
Put/Call Ratio data fetcher.

Collects CBOE put/call ratio data for equity and index options.
Primary source: CBOE public data (free).
Mock mode: returns synthetic put/call ratio data.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base_alt import BaseFetcher


class PutCallFetcher(BaseFetcher):
    """Fetches Put/Call Ratio data from CBOE."""

    SOURCE_NAME = "put_call_ratio"
    CONFIG_KEY = ""  # CBOE public data is free, but we mock by default

    CBOE_PCR_URL = "https://cdn.cboe.com/api/us/daily_market_statistics/spx/pc_data.json"

    async def fetch(self) -> dict[str, Any]:
        """Fetch put/call ratio data."""
        try:
            if self._is_mock:
                data = self._generate_mock_data()
                self._record_success()
                return self._build_result(data, extra={"method": "mock"})

            # Try CBOE public data
            try:
                data = await self._fetch_cboe()
                self._record_success()
                return self._build_result(data, extra={"method": "cboe"})
            except Exception as e:
                self.logger.warning(f"CBOE fetch failed: {e}, returning mock")

            data = self._generate_mock_data()
            self._record_success()
            return self._build_result(data, extra={"method": "mock_fallback"})

        except Exception as e:
            self._record_error(str(e))
            return self._build_result(
                self._generate_mock_data(),
                extra={"method": "mock_error", "error": str(e)},
            )

    async def _fetch_cboe(self) -> dict[str, Any]:
        """Fetch from CBOE public API."""
        raw = await self._get_json(self.CBOE_PCR_URL)

        # Parse latest entry
        latest = raw[-1] if isinstance(raw, list) and raw else {}
        equity_pcr = float(latest.get("equity_pcr", 0))
        index_pcr = float(latest.get("index_pcr", 0))
        total_pcr = float(latest.get("total_pcr", 0))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity_put_call_ratio": equity_pcr,
            "index_put_call_ratio": index_pcr,
            "total_put_call_ratio": total_pcr,
            "equity_call_volume": int(latest.get("equity_call_volume", 0)),
            "equity_put_volume": int(latest.get("equity_put_volume", 0)),
            "index_call_volume": int(latest.get("index_call_volume", 0)),
            "index_put_volume": int(latest.get("index_put_volume", 0)),
            "pcr_signal": self._interpret_pcr(total_pcr),
            "is_extreme": total_pcr > 1.3 or total_pcr < 0.5,
        }

    def _interpret_pcr(self, pcr: float) -> str:
        """Interpret put/call ratio as a signal."""
        if pcr > 1.3:
            return "extreme_fear"  # Contrarian bullish
        elif pcr > 1.0:
            return "fear"
        elif pcr > 0.8:
            return "neutral"
        elif pcr > 0.5:
            return "complacency"
        else:
            return "extreme_complacency"  # Contrarian bearish

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock put/call ratio data."""
        equity_pcr = round(random.uniform(0.5, 1.5), 3)
        index_pcr = round(random.uniform(0.4, 1.2), 3)
        total_pcr = round((equity_pcr + index_pcr) / 2, 3)

        call_vol = random.randint(500000, 2000000)
        put_vol = int(call_vol * total_pcr)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity_put_call_ratio": equity_pcr,
            "index_put_call_ratio": index_pcr,
            "total_put_call_ratio": total_pcr,
            "equity_call_volume": call_vol,
            "equity_put_volume": put_vol,
            "index_call_volume": random.randint(300000, 1500000),
            "index_put_volume": random.randint(200000, 1200000),
            "pcr_signal": self._interpret_pcr(total_pcr),
            "is_extreme": total_pcr > 1.3 or total_pcr < 0.5,
        }
