"""
GEXMetrix data fetcher — collects Gamma Exposure (GEX) data from GEXMetrix API.

Primary data source for the monitoring system. Fetches per-symbol option chain data,
parses individual strikes (call/put GEX, OI, volume), and computes aggregate metrics
(net_gex, call_wall, put_wall, zero_gamma_level).

Endpoint: api.gexmetrix.com/api/files/{symbol}/latest
Typical latency: ~9.87s (largest payload, 1600+ strikes per symbol)
"""

import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# Symbols tracked by GEXMetrix
GEX_SYMBOLS = ["SPX", "SPY", "QQQ", "IWM", "NDX", "VIX"]

# GEX aggregation constants
MULTIPLIER = 100       # Standard options multiplier
MIN_OI_FILTER = 100    # Minimum OI to include a strike (filter deep OTM)

# GEXMetrix API base URL
GEXMETRIX_BASE_URL = "https://api.gexmetrix.com/api/files"


class GEXMetrixFetcher(BaseFetcher):
    """Fetcher for GEXMetrix Gamma Exposure data.

    Collects per-symbol option chain JSON, parses individual strikes,
    and produces both snapshot-level aggregates and per-strike breakdowns.
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)
        self._symbols = GEX_SYMBOLS

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "GEXMetrix"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"

    async def fetch(self) -> dict:
        """Fetch latest GEX data for all tracked symbols.

        Returns:
            dict with keys:
                - snapshots: list of per-symbol snapshot dicts
                - strikes: list of per-strike dicts (all symbols combined)
                - fetch_timestamp: ISO timestamp of collection
        """
        now = datetime.now(timezone.utc)
        all_snapshots = []
        all_strikes = []

        for symbol in self._symbols:
            try:
                url = f"{GEXMETRIX_BASE_URL}/{symbol.lower()}/latest"
                headers = {}
                if self.config.gexmetrix_api_key:
                    headers["Authorization"] = f"Bearer {self.config.gexmetrix_api_key}"

                response = await self._http_get(url, headers=headers)
                data = response.json()

                # Parse snapshot-level metrics
                snapshot = self._parse_snapshot(symbol, data, now)
                all_snapshots.append(snapshot)

                # Parse per-strike data
                strikes = self._parse_strikes(symbol, data, now, snapshot_id=0)
                all_strikes.extend(strikes)

                self.logger.info(
                    f"[GEXMetrix] {symbol}: net_gex={snapshot['net_gex']:.0f}, "
                    f"{len(strikes)} strikes parsed"
                )

            except Exception as exc:
                self.logger.error(f"[GEXMetrix] Failed to fetch {symbol}: {exc}")
                # Continue with other symbols — single-symbol failure is non-fatal

        return {
            "snapshots": all_snapshots,
            "strikes": all_strikes,
            "fetch_timestamp": now.isoformat(),
            "symbol_count": len(all_snapshots),
            "total_strikes": len(all_strikes),
        }

    def _mock_data(self) -> dict:
        """Return realistic mock GEX data for all symbols."""
        now = datetime.now(timezone.utc)
        snapshots = []
        strikes = []

        # Reference spot prices for mock data
        spot_prices = {
            "SPX": 5750.0, "SPY": 575.0, "QQQ": 510.0,
            "IWM": 225.0, "NDX": 20500.0, "VIX": 15.0,
        }

        for symbol in self._symbols:
            spot = spot_prices.get(symbol, 5000.0)
            net_gex = random.uniform(-2e9, 1e9)
            call_gex = abs(random.gauss(1.2e9, 3e8))
            put_gex = -abs(random.gauss(1.5e9, 4e8))
            zero_gamma = spot * random.uniform(0.97, 1.03)
            call_wall = spot * random.uniform(1.01, 1.05)
            put_wall = spot * random.uniform(0.95, 0.99)

            snapshot = {
                "symbol": symbol,
                "timestamp": now.isoformat(),
                "filename": f"mock_{symbol}_{now.strftime('%Y%m%d_%H%M%S')}.json",
                "net_gex": round(net_gex, 2),
                "call_gex": round(call_gex, 2),
                "put_gex": round(put_gex, 2),
                "zero_gamma_level": round(zero_gamma, 2),
                "call_wall": round(call_wall, 2),
                "put_wall": round(put_wall, 2),
                "spot_price": round(spot, 2),
                "total_gamma": round(abs(call_gex) + abs(put_gex), 2),
                "file_size": random.randint(5_000_000, 20_000_000),
                "quality_score": round(random.uniform(0.85, 0.99), 3),
                "data_lag_seconds": random.randint(30, 120),
                "oi_coverage_pct": round(random.uniform(90.0, 99.5), 2),
            }
            snapshots.append(snapshot)

            # Generate mock strikes around the spot price
            strike_step = max(spot * 0.005, 1.0)  # 0.5% step or $1 min
            for i in range(-20, 21):
                strike_price = round(spot + i * strike_step, 2)
                s_call_gex = random.gauss(5e7, 2e7)
                s_put_gex = -random.gauss(6e7, 2.5e7)
                strikes.append({
                    "snapshot_id": 0,
                    "symbol": symbol,
                    "timestamp": now.isoformat(),
                    "strike": strike_price,
                    "call_gex": round(max(s_call_gex, 0), 2),
                    "put_gex": round(min(s_put_gex, 0), 2),
                    "call_oi": random.randint(500, 50000),
                    "put_oi": random.randint(500, 50000),
                    "call_vol": random.randint(100, 10000),
                    "put_vol": random.randint(100, 10000),
                    "net_gex": round(s_call_gex + s_put_gex, 2),
                })

        return {
            "snapshots": snapshots,
            "strikes": strikes,
            "fetch_timestamp": now.isoformat(),
            "symbol_count": len(snapshots),
            "total_strikes": len(strikes),
        }

    def _validate_data(self, data: dict) -> bool:
        """Validate GEXMetrix response structure."""
        if not super()._validate_data(data):
            return False
        if "snapshots" not in data:
            self.logger.warning("[GEXMetrix] Missing 'snapshots' key")
            return False
        if not isinstance(data["snapshots"], list):
            self.logger.warning("[GEXMetrix] 'snapshots' is not a list")
            return False
        return True

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _parse_snapshot(
        self, symbol: str, raw: dict, ts: datetime
    ) -> dict:
        """Parse a raw GEXMetrix JSON into a snapshot dict.

        Args:
            symbol: Ticker symbol (SPX, SPY, etc.)
            raw: Raw JSON response from GEXMetrix API.
            ts: Collection timestamp.

        Returns:
            Snapshot dict conforming to GEXSnapshotCreate model.
        """
        options = raw.get("options", [])
        spot = raw.get("spot", raw.get("underlying_price", 0.0))

        call_gex_total = 0.0
        put_gex_total = 0.0
        max_call_gex_strike = spot
        max_put_gex_strike = spot
        max_call_gex_val = 0.0
        max_put_gex_val = 0.0
        zero_gamma_candidates = []

        for opt in options:
            strike = opt.get("strike", 0)
            gamma = opt.get("gamma", 0)
            oi = opt.get("openInterest", opt.get("oi", 0))
            opt_type = opt.get("type", opt.get("optionType", "")).upper()

            if oi < MIN_OI_FILTER:
                continue

            gex_value = gamma * oi * MULTIPLIER * spot * spot * 0.01

            if opt_type == "CALL":
                call_gex_total += gex_value
                if gex_value > max_call_gex_val:
                    max_call_gex_val = gex_value
                    max_call_gex_strike = strike
                zero_gamma_candidates.append((strike, gex_value))
            elif opt_type == "PUT":
                put_gex_total -= gex_value  # put GEX is negative
                if abs(gex_value) > max_put_gex_val:
                    max_put_gex_val = abs(gex_value)
                    max_put_gex_strike = strike
                zero_gamma_candidates.append((strike, -gex_value))

        net_gex = call_gex_total + put_gex_total

        # Zero gamma level: strike where cumulative GEX crosses zero
        zero_gamma_level = self._find_zero_gamma_level(zero_gamma_candidates, spot)

        return {
            "symbol": symbol,
            "timestamp": ts.isoformat(),
            "filename": raw.get("filename", f"{ts.strftime('%Y%m%d_%H%M%S')}.json"),
            "net_gex": round(net_gex, 2),
            "call_gex": round(call_gex_total, 2),
            "put_gex": round(put_gex_total, 2),
            "zero_gamma_level": round(zero_gamma_level, 2),
            "call_wall": round(max_call_gex_strike, 2),
            "put_wall": round(max_put_gex_strike, 2),
            "spot_price": round(spot, 2),
            "total_gamma": round(abs(call_gex_total) + abs(put_gex_total), 2),
            "file_size": raw.get("file_size", 0),
            "quality_score": raw.get("quality_score", 0.95),
            "data_lag_seconds": raw.get("data_lag_seconds", 60),
            "oi_coverage_pct": raw.get("oi_coverage_pct", 98.0),
        }

    def _parse_strikes(
        self, symbol: str, raw: dict, ts: datetime, snapshot_id: int = 0
    ) -> list[dict]:
        """Parse per-strike GEX/OI data from raw GEXMetrix options array.

        Aggregates by strike price (summing across expirations).

        Args:
            symbol: Ticker symbol.
            raw: Raw JSON response with 'options' array.
            ts: Collection timestamp.
            snapshot_id: FK to gex_snapshots (0 if not yet inserted).

        Returns:
            List of strike dicts conforming to GEXStrikeCreate model.
        """
        options = raw.get("options", [])
        spot = raw.get("spot", raw.get("underlying_price", 0.0))

        # Aggregate by strike
        strike_agg: dict[float, dict] = {}
        for opt in options:
            strike = opt.get("strike", 0)
            gamma = opt.get("gamma", 0)
            oi = opt.get("openInterest", opt.get("oi", 0))
            vol = opt.get("volume", 0)
            opt_type = opt.get("type", opt.get("optionType", "")).upper()

            if oi < MIN_OI_FILTER:
                continue

            gex_value = gamma * oi * MULTIPLIER * spot * spot * 0.01

            if strike not in strike_agg:
                strike_agg[strike] = {
                    "call_gex": 0.0, "put_gex": 0.0,
                    "call_oi": 0, "put_oi": 0,
                    "call_vol": 0, "put_vol": 0,
                }

            if opt_type == "CALL":
                strike_agg[strike]["call_gex"] += gex_value
                strike_agg[strike]["call_oi"] += oi
                strike_agg[strike]["call_vol"] += vol
            elif opt_type == "PUT":
                strike_agg[strike]["put_gex"] -= gex_value  # negative direction
                strike_agg[strike]["put_oi"] += oi
                strike_agg[strike]["put_vol"] += vol

        result = []
        for strike, agg in sorted(strike_agg.items()):
            result.append({
                "snapshot_id": snapshot_id,
                "symbol": symbol,
                "timestamp": ts.isoformat(),
                "strike": round(strike, 2),
                "call_gex": round(agg["call_gex"], 2),
                "put_gex": round(agg["put_gex"], 2),
                "call_oi": agg["call_oi"],
                "put_oi": agg["put_oi"],
                "call_vol": agg["call_vol"],
                "put_vol": agg["put_vol"],
                "net_gex": round(agg["call_gex"] + agg["put_gex"], 2),
            })

        return result

    @staticmethod
    def _find_zero_gamma_level(candidates: list[tuple], spot: float) -> float:
        """Find the strike closest to where cumulative GEX crosses zero.

        Simple heuristic: find the strike closest to spot where net GEX
        transitions from positive to negative.

        Args:
            candidates: List of (strike, gex_value) tuples.
            spot: Current spot price.

        Returns:
            Estimated zero gamma strike level.
        """
        if not candidates:
            return spot

        # Sort by strike
        sorted_candidates = sorted(candidates, key=lambda x: x[0])

        # Find crossing point nearest to spot
        best_strike = spot
        min_distance = float("inf")
        for strike, gex in sorted_candidates:
            if abs(gex) < min_distance and abs(strike - spot) / spot < 0.05:
                min_distance = abs(gex)
                best_strike = strike

        return best_strike
