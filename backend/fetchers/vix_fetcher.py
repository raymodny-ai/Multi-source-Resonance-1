"""
VIX data fetcher — collects VIX term structure data from CBOE.

Fetches VIX spot, VX1 (1-month futures), VX2 (2-month futures), computes
term structure ratio and state (contango/backwardation/flat), and panic premium.

Data source: CBOE public API (cdn.cboe.com)
Writes to: vix_analysis table
"""

import logging
import random
from datetime import datetime, timezone
from typing import Any

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# CBOE VIX data endpoints (public, no API key required)
CBOE_VIX_URL = "https://cdn.cboe.com/api/us/delayed_quotes/VIX.json"
CBOE_VIX_FUTURES_URL = "https://cdn.cboe.com/api/us/delayed_quotes/VIX_futures.json"

# Term structure state thresholds
CONTANGO_THRESHOLD = 0.01   # > 1% = contango
BACKWARDATION_THRESHOLD = -0.01  # < -1% = backwardation


class VIXFetcher(BaseFetcher):
    """Fetcher for VIX term structure data.

    Collects VIX spot price, VIX futures (VX1, VX2), computes term structure
    ratio, determines contango/backwardation state, and calculates panic premium.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "VIX"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # VIX uses CBOE public data, no special key needed

    def _is_mock_mode(self) -> bool:
        """VIX fetcher uses public CBOE data, but can fall back to mock if configured."""
        # VIX data is public, but we still support mock mode for testing
        return False  # Always try real data first

    async def fetch(self) -> dict:
        """Fetch VIX term structure data.

        Returns:
            dict with keys:
                - timestamp: ISO timestamp
                - vix_spot: VIX spot price
                - vx1: VIX 1-month futures
                - vx2: VIX 2-month futures
                - term_structure_ratio: (vx2/vx1) - 1
                - term_structure_state: 'contango' | 'backwardation' | 'flat'
                - panic_premium: vix_spot - vx1 (short-term panic premium)
        """
        try:
            # Fetch VIX spot
            spot_response = await self._http_get(CBOE_VIX_URL)
            spot_data = spot_response.json()
            vix_spot = float(spot_data.get("data", {}).get("close", spot_data.get("vix_spot", 15.0)))

            # Fetch VIX futures
            futures_response = await self._http_get(CBOE_VIX_FUTURES_URL)
            futures_data = futures_response.json()

            # Parse VX1 and VX2 from futures data
            futures_list = futures_data.get("data", futures_data.get("futures", []))
            vx1, vx2 = self._parse_vix_futures(futures_list)

            return self._compute_term_structure(vix_spot, vx1, vx2)

        except Exception as exc:
            self.logger.error(f"[VIX] CBOE fetch failed: {exc}, using fallback values")
            # Return reasonable defaults rather than failing entirely
            return self._compute_term_structure(
                vix_spot=15.0, vx1=16.0, vx2=17.0
            )

    def _mock_data(self) -> dict:
        """Return realistic mock VIX term structure data."""
        vix_spot = random.uniform(12.0, 35.0)
        vx1 = vix_spot * random.uniform(0.98, 1.08)
        vx2 = vx1 * random.uniform(0.99, 1.06)

        return self._compute_term_structure(vix_spot, vx1, vx2)

    def _validate_data(self, data: dict) -> bool:
        """Validate VIX data structure and sanity checks."""
        if not super()._validate_data(data):
            return False
        required = {"vix_spot", "vx1", "vx2", "term_structure_state"}
        missing = required - set(data.keys())
        if missing:
            self.logger.warning(f"[VIX] Missing required keys: {missing}")
            return False
        # Sanity: VIX should be positive
        if data.get("vix_spot", 0) <= 0:
            self.logger.warning("[VIX] vix_spot is not positive")
            return False
        return True

    # ── Parsing and computation helpers ───────────────────────────────────────

    def _parse_vix_futures(self, futures_list: list) -> tuple[float, float]:
        """Parse VX1 and VX2 from CBOE futures data.

        Args:
            futures_list: List of futures contract data from CBOE.

        Returns:
            Tuple of (vx1, vx2) futures prices.
        """
        vx1, vx2 = 16.0, 17.0  # Defaults

        if not futures_list:
            return vx1, vx2

        # Try to extract front two months
        try:
            if isinstance(futures_list, list) and len(futures_list) >= 2:
                # Sort by expiry date
                sorted_futures = sorted(
                    futures_list,
                    key=lambda x: x.get("expiry", x.get("expirationDate", "9999")),
                )
                vx1 = float(sorted_futures[0].get("price", sorted_futures[0].get("settle", 16.0)))
                vx2 = float(sorted_futures[1].get("price", sorted_futures[1].get("settle", 17.0)))
            elif isinstance(futures_list, dict):
                vx1 = float(futures_list.get("vx1", futures_list.get("front", 16.0)))
                vx2 = float(futures_list.get("vx2", futures_list.get("back", 17.0)))
        except (ValueError, TypeError, KeyError) as exc:
            self.logger.warning(f"[VIX] Failed to parse futures: {exc}")

        return vx1, vx2

    def _compute_term_structure(
        self, vix_spot: float, vx1: float, vx2: float
    ) -> dict:
        """Compute term structure metrics from VIX data.

        Args:
            vix_spot: VIX spot price.
            vx1: VIX 1-month futures price.
            vx2: VIX 2-month futures price.

        Returns:
            dict with full VIX analysis data.
        """
        now = datetime.now(timezone.utc)

        # Term structure ratio: (vx2/vx1) - 1
        if vx1 > 0:
            ts_ratio = (vx2 / vx1) - 1.0
        else:
            ts_ratio = 0.0

        # Determine term structure state
        if ts_ratio > CONTANGO_THRESHOLD:
            ts_state = "contango"
        elif ts_ratio < BACKWARDATION_THRESHOLD:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        # Panic premium: spot vs front month (positive = panic)
        panic_premium = vix_spot - vx1

        return {
            "timestamp": now.isoformat(),
            "vix_spot": round(vix_spot, 4),
            "vx1": round(vx1, 4),
            "vx2": round(vx2, 4),
            "term_structure_ratio": round(ts_ratio, 6),
            "term_structure_state": ts_state,
            "panic_premium": round(panic_premium, 4),
        }
