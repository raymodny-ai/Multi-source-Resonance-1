"""
Put/Call Ratio data fetcher.

Primary source: CBOE public data (free).
Fallback: mock with ``is_mock=True, data_source="mock"``.

FIX-12: the previous fallback path returned the mock dict without
``_internal_mock=True`` (or any other marker), so the data writer could
not tell real from mock and the UI could not flag it. The mock path
now also sets ``data_source="mock"`` and the fetch path tags real data
with ``data_source="cboe"`` for downstream provenance.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class PutCallFetcher(BaseFetcher):
    """Fetches Put/Call Ratio data from CBOE."""

    @property
    def source_name(self) -> str:
        return "put_call_ratio"

    @property
    def _mock_mode_key(self) -> str:
        # CBOE is free public data, but the URL changed and the JSON shape
        # is not stable. We attempt real first, fall back to mock.
        return "gexmetrix"

    CBOE_PCR_URL = "https://cdn.cboe.com/api/us/daily_market_statistics/spx/pc_data.json"

    async def fetch(self) -> dict:
        """Fetch put/call ratio data.

        FIX-12: both the real path and the mock path now set a stable
        ``data_source`` field and (for mock) ``_internal_mock=True`` so
        the data writer can persist the mock marker into the DB column.
        """
        try:
            data = await self._fetch_cboe()
            if data is not None:
                data["data_source"] = "cboe"
                return data
        except Exception as e:
            self.logger.warning(f"CBOE put/call fetch failed: {e}, returning mock")

        # Mock fallback — mark it explicitly so it is never confused with
        # a real reading.
        mock = self._generate_mock_data()
        mock["_internal_mock"] = True
        mock["data_source"] = "mock"
        return mock

    def _mock_data(self) -> dict:
        """Return mock put/call ratio data."""
        mock = self._generate_mock_data()
        mock["_internal_mock"] = True
        mock["data_source"] = "mock"
        return mock

    async def _fetch_cboe(self) -> dict[str, Any] | None:
        """Fetch from CBOE public API. Returns None on unusable payload."""
        raw = await self._get_json(self.CBOE_PCR_URL)

        if not raw or not isinstance(raw, list) or not raw:
            return None

        # Parse latest entry
        latest = raw[-1] if isinstance(raw, list) and raw else {}
        equity_pcr = float(latest.get("equity_pcr", 0) or 0)
        index_pcr = float(latest.get("index_pcr", 0) or 0)
        total_pcr = float(latest.get("total_pcr", 0) or 0)

        # FIX-13: if all three ratios are 0 the response is unusable
        # (e.g. CBOE returned a placeholder during off-hours). Return None
        # so the caller falls through to mock rather than emitting
        # fabricated data.
        if equity_pcr == 0 and index_pcr == 0 and total_pcr == 0:
            return None

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity_put_call_ratio": equity_pcr,
            "index_put_call_ratio": index_pcr,
            "total_put_call_ratio": total_pcr,
            "equity_call_volume": int(latest.get("equity_call_volume", 0) or 0),
            "equity_put_volume": int(latest.get("equity_put_volume", 0) or 0),
            "index_call_volume": int(latest.get("index_call_volume", 0) or 0),
            "index_put_volume": int(latest.get("index_put_volume", 0) or 0),
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
