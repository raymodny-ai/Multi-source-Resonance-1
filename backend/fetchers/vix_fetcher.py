"""
VIX data fetcher — collects VIX term structure data from FRED (St. Louis Fed).

Fetches VIX spot (VIXCLS series) + 3M VIX proxy (VXVCLS series, the CBOE
S&P 500 3-Month Volatility Index), computes term structure ratio and state
(contango/backwardation/flat), panic premium, and vol regime.

Data source: FRED public CSV (fred.stlouisfed.org/graph/fredgraph.csv)
Writes to:
    - vix_analysis (per-cycle intraday snapshots)
    - vix_term_structure (daily PK, historical)
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.request import urlopen

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# FRED series ids (CBOE-derived volatility indices)
FRED_VIXCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"   # VIX spot
FRED_VXVCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS"   # 3M VIX (term-structure back-end proxy)

# Term structure state thresholds (in ratio terms)
CONTANGO_THRESHOLD = 0.02   # (vx_3m / vix_spot - 1) > 2% = contango
BACKWARDATION_THRESHOLD = -0.02  # < -2% = backwardation

# Vol regime thresholds
REGIME_LOW_MAX = 15.0
REGIME_ELEVATED_MIN = 25.0
REGIME_PANIC_MIN = 35.0


class VIXFetcher(BaseFetcher):
    """Fetcher for VIX term structure data via FRED.

    Strategy:
        1. Fetch last 30 days VIXCLS + VXVCLS from FRED CSV (no API key needed).
        2. Latest row → populate vix_analysis (intraday per-cycle insert)
                         + vix_term_structure (daily PK).
        3. All rows → batched daily snapshots in 'history' field for backfill.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "VIX"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # VIX uses public FRED data, no key needed

    def _is_mock_mode(self) -> bool:
        return False  # Always try real FRED first

    async def fetch(self) -> dict:
        """Fetch VIX term structure data via FRED VIXCLS + VXVCLS series.

        Returns:
            dict with keys:
                - timestamp: ISO timestamp (latest fetch time)
                - date: YYYY-MM-DD (latest trading day)
                - vix_spot: VIX spot price
                - vx_3m_proxy: VXVCLS (CBOE 3M volatility index, back-end proxy)
                - vx1: same as vx_3m_proxy (legacy field for vix_analysis compat)
                - vx2: same as vx_3m_proxy (legacy field for vix_analysis compat)
                - term_structure_ratio: (vx_3m / vix_spot - 1) * 100
                - term_structure_state: 'contango' | 'backwardation' | 'flat'
                - panic_premium: vix_spot - vx_3m_proxy
                - regime: 'low' | 'normal' | 'elevated' | 'panic'
                - history: list of past 30 daily snapshots [{date, vix_spot, vx_3m_proxy, ...}]
        """
        try:
            # Fetch FRED CSVs synchronously (urllib, no API key needed)
            vix_spot, vx_3m, history = await self._fetch_fred_vix()

            if vix_spot is None or vx_3m is None:
                raise ValueError("FRED returned no usable VIX/VXV data")

            latest_date = history[-1]["date"] if history else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return self._build_payload(
                date=latest_date,
                vix_spot=vix_spot,
                vx_3m=vx_3m,
                history=history,
            )
        except Exception as exc:
            self.logger.warning(f"[VIX] FRED fetch failed: {exc}, using mock fallback")
            mock = self._mock_data()
            mock["_internal_mock"] = True
            return mock

    async def _fetch_fred_vix(self) -> tuple[Optional[float], Optional[float], list]:
        """Fetch last 30 days VIXCLS + VXVCLS from FRED.

        Returns:
            (vix_spot, vx_3m, history) — latest values + 30-day daily series.
        """
        import asyncio

        def _fetch_sync(url: str) -> dict[str, float]:
            """Parse FRED CSV → {date_str: value} dict (only business days with values)."""
            try:
                with urlopen(url, timeout=8) as r:
                    text = r.read().decode()
            except Exception as e:
                self.logger.warning(f"[VIX] FRED fetch error for {url}: {e}")
                return {}
            result = {}
            for line in text.strip().split("\n")[1:]:  # skip header
                if "," not in line:
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    continue
                d, v = parts[0].strip(), parts[1].strip()
                if v == "." or not v:  # FRED uses "." for missing
                    continue
                try:
                    result[d] = float(v)
                except ValueError:
                    continue
            return result

        # Fetch both series in parallel via asyncio.to_thread
        vix_series, vxv_series = await asyncio.gather(
            asyncio.to_thread(_fetch_sync, FRED_VIXCLS_URL),
            asyncio.to_thread(_fetch_sync, FRED_VXVCLS_URL),
        )

        if not vix_series or not vxv_series:
            return None, None, []

        # Align dates (only dates present in both series)
        common_dates = sorted(set(vix_series.keys()) & set(vxv_series.keys()))
        if not common_dates:
            return None, None, []

        # Last 30 trading days
        recent = common_dates[-30:]
        history = [
            {"date": d, "vix_spot": vix_series[d], "vx_3m_proxy": vxv_series[d]}
            for d in recent
        ]

        latest_date = recent[-1]
        return vix_series[latest_date], vxv_series[latest_date], history

    def _build_payload(self, date: str, vix_spot: float, vx_3m: float, history: list) -> dict:
        """Compute term-structure metrics and build the write payload."""
        ratio = (vx_3m / vix_spot - 1.0) if vix_spot else 0.0
        if ratio > CONTANGO_THRESHOLD:
            state = "contango"
        elif ratio < BACKWARDATION_THRESHOLD:
            state = "backwardation"
        else:
            state = "flat"
        panic_premium = vix_spot - vx_3m

        if vix_spot < REGIME_LOW_MAX:
            regime = "low"
        elif vix_spot < REGIME_ELEVATED_MIN:
            regime = "normal"
        elif vix_spot < REGIME_PANIC_MIN:
            regime = "elevated"
        else:
            regime = "panic"

        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "timestamp": now_iso,
            "date": date,
            "vix_spot": vix_spot,
            "vx_3m_proxy": vx_3m,
            # Legacy field names for vix_analysis compat
            "vx1": vx_3m,
            "vx2": vx_3m,
            "term_structure_ratio": round(ratio, 4),
            "term_structure_state": state,
            "panic_premium": round(panic_premium, 4),
            "regime": regime,
            "history": history,
        }

    def _mock_data(self) -> dict:
        """Return realistic mock VIX term structure data (last resort fallback)."""
        vix_spot = random.uniform(12.0, 35.0)
        vx_3m = vix_spot * random.uniform(0.92, 1.08)
        history = []
        # Mock 30-day series with mild mean-reverting walk
        for i in range(30):
            d = (datetime.now(timezone.utc) - timedelta(days=30 - i)).strftime("%Y-%m-%d")
            v = vix_spot + random.uniform(-3, 3)
            v_3m = v * random.uniform(0.95, 1.05)
            history.append({"date": d, "vix_spot": round(v, 2), "vx_3m_proxy": round(v_3m, 2)})
        payload = self._build_payload(
            date=history[-1]["date"],
            vix_spot=vix_spot,
            vx_3m=vx_3m,
            history=history,
        )
        # Mark the mock payload so the wrapping layer sets is_mock=True.
        payload["_internal_mock"] = True
        return payload

    def _validate_data(self, data: dict) -> bool:
        if not super()._validate_data(data):
            return False
        required = {"vix_spot", "vx_3m_proxy", "term_structure_state"}
        if not required.issubset(data.keys()):
            self.logger.warning(f"[VIX] Missing required keys: {required - set(data.keys())}")
            return False
        if data.get("vix_spot", 0) <= 0:
            self.logger.warning("[VIX] vix_spot is not positive")
            return False
        return True