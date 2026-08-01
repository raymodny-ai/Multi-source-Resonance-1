"""
VIX term structure data fetcher.

Collects VIX spot, VX1 (1-month), VX2 (2-month) futures, term structure
ratio and state (contango / backwardation / flat).
Primary source: CBOE public CDN (free, no key).
Mock mode: returns synthetic VIX term structure data matching VIXSnapshot model.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class VIXTermFetcher(BaseFetcher):
    """Fetches VIX term structure data from CBOE."""

    @property
    def source_name(self) -> str:
        return "vix_term_structure"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # CBOE public data is free

    # ── CBOE public CSV sources (replaces the retired daily_market_statistics JSON)
    #    All return HTTP 200 with the default client UA.
    CBOE_VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
    # CBOE VX1/VX2 History CSVs are broken (only contain a couple of rows).
    # Use FRED VXVCLS (VIX 3-month implied vol, daily since 2007) as the 3M proxy.
    FRED_VXVCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS"
    CBOE_VX1_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VX1_History.csv"
    CBOE_VX2_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VX2_History.csv"

    async def fetch(self) -> dict:
        """Fetch VIX term structure data."""
        try:
            return await self._fetch_cboe()
        except Exception as e:
            self.logger.warning(f"CBOE VIX fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock VIX term structure data."""
        return self._generate_mock_data()

    async def _fetch_cboe(self) -> dict[str, Any]:
        """Fetch VIX spot + VX1/VX2 futures from CBOE public history CSVs.

        CSV row format (chronological ASC, last row = latest):
          VIX_History: DATE,OPEN,HIGH,LOW,CLOSE
          VX1/VX2_History: DATE,VX1 | DATE,VX2
        """
        vix_csv = await self._http_get(self.CBOE_VIX_URL)
        # httpx times out on FRED reliably; use stdlib urllib for VXVCLS.
        vxv_text = await self._fetch_urllib_text(self.FRED_VXVCLS_URL)

        def _parse_last(text: str, col: int) -> float:
            lines = [l for l in text.strip().splitlines() if l.strip()]
            latest = lines[-1].split(",")
            return float(latest[col])

        def _parse_last_date(text: str) -> str:
            """Return the ISO date of the last CSV row (CBOE MM/DD/YYYY)."""
            lines = [l for l in text.strip().splitlines() if l.strip()]
            last = lines[-1].split(",")[0].strip()
            try:
                return datetime.strptime(last, "%m/%d/%Y").date().isoformat()
            except ValueError:
                return last

        # VIX spot (CBOE daily close); VXVCLS already YYYY-MM-DD from FRED.
        vix_spot = _parse_last(vix_csv.text, 4)  # CLOSE
        latest_date = _parse_last_date(vix_csv.text)
        vx3 = None
        for line in vxv_text.strip().splitlines()[1:]:
            if line.startswith(latest_date + ","):
                vx3 = float(line.split(",")[1])
                break
        if vx3 is None:
            # FRED lags a day; fall back to its newest value.
            lines = [l for l in vxv_text.strip().splitlines() if l.strip()]
            vx3 = float(lines[-1].split(",")[1])

        # Compute term structure (VXVCLS = 3M proxy)
        ts_ratio = (vx3 / vix_spot - 1) if vix_spot > 0 else 0.0
        if ts_ratio > 0.02:
            ts_state = "contango"
        elif ts_ratio < -0.02:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        panic_premium = vix_spot - vx3 if vix_spot and vx3 else 0.0

        if vix_spot >= 30:
            regime = "high_vol"
        elif vix_spot >= 20:
            regime = "elevated"
        else:
            regime = "normal"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": latest_date,          # -> writes to vix_term_structure
            "vix_spot": vix_spot,
            "vx_3m_proxy": round(vx3, 2),  # -> vx_3m_proxy column
            "vx1": vix_spot,               # keep for vix_analysis compat
            "vx2": vx3,
            "term_structure_ratio": round(ts_ratio, 4),
            "term_structure_state": ts_state,
            "panic_premium": round(panic_premium, 2),
            "regime": regime,
        }

    @staticmethod
    async def _fetch_urllib_text(url: str) -> str:
        """Fetch plain text via stdlib urllib (httpx times out on FRED)."""
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "MultiSourceResonance/3.1"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock VIX term structure data."""
        vix_spot = round(random.uniform(12, 35), 2)
        vx1 = round(vix_spot + random.uniform(-2, 3), 2)
        vx2 = round(vx1 + random.uniform(-1, 4), 2)

        ts_ratio = (vx2 / vx1 - 1) if vx1 > 0 else 0.0
        if ts_ratio > 0.02:
            ts_state = "contango"
        elif ts_ratio < -0.02:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        panic_premium = round(vix_spot - vx1, 2)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vix_spot": vix_spot,
            "vx1": vx1,
            "vx2": vx2,
            "term_structure_ratio": round(ts_ratio, 4),
            "term_structure_state": ts_state,
            "panic_premium": panic_premium,
        }
