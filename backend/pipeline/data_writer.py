"""
Data writer for persisting pipeline results to SQLite.
Handles batch writes, validation audit log, and gateway snapshots.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from backend.database import get_db

logger = logging.getLogger(__name__)


class DataWriter:
    """Persists pipeline data to the SQLite database.

    Responsibilities:
        - Write fetcher results to their respective domain tables
        - Write validation audit log entries (resolves 0-row anomaly)
        - Write gateway snapshots (Layer1/Layer2 JSON payloads)
        - Batch insert optimisation for strike-level data
        - Write signal alerts from scoring phase
    """

    # ── Fetch result persistence ───────────────────────────────────────────────

    async def write_fetch_results(self, results: dict[str, dict]) -> dict[str, int]:
        """Write collected fetcher data to the appropriate domain tables.

        Args:
            results: Mapping of source_name -> fetched data dict.

        Returns:
            Dict mapping source_name -> number of rows written.
        """
        written: dict[str, int] = {}
        now = datetime.now(timezone.utc).isoformat()

        async with get_db() as conn:
            for source, data in results.items():
                try:
                    count = await self._write_source_data(conn, source, data, now)
                    written[source] = count
                    logger.debug(f"Written {count} row(s) for source '{source}'")
                except Exception as exc:
                    logger.error(
                        f"Failed to write data for '{source}': {exc}",
                        exc_info=True,
                    )
                    written[source] = 0

        return written

    async def _write_source_data(
        self,
        conn,
        source: str,
        data: dict,
        now: str,
    ) -> int:
        """Route a single source's data to the correct table(s)."""
        source_lower = source.lower()

        if source_lower == "gexmetrix":
            return await self._write_gex_snapshot(conn, data, now)
        elif source_lower in ("vix", "cboe"):
            return await self._write_vix_analysis(conn, data, now)
        elif source_lower in ("darkpool", "put_call", "sector"):
            return await self._write_dark_pool_metrics(conn, data, now)
        elif source_lower == "crypto":
            return await self._write_crypto_derivatives(conn, data, now)
        else:
            # Generic: write to gateway_snapshots as audit trail
            return await self._write_gateway_snapshot(
                conn, source, data, now, status="OK"
            )

    # ── GEX snapshot writer ────────────────────────────────────────────────────

    async def _write_gex_snapshot(self, conn, data: dict, now: str) -> int:
        """Insert a GEX snapshot and associated strikes (batch)."""
        rows = 0
        ts = data.get("_meta", {}).get("fetched_at", now)

        # Insert snapshot summary
        await conn.execute(
            """INSERT INTO gex_snapshots
               (symbol, timestamp, filename, net_gex, call_gex, put_gex,
                zero_gamma_level, call_wall, put_wall, spot_price,
                total_gamma, file_size, quality_score, data_lag_seconds,
                oi_coverage_pct)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("symbol", "SPX"),
                ts,
                data.get("filename", "unknown"),
                data.get("net_gex"),
                data.get("call_gex"),
                data.get("put_gex"),
                data.get("zero_gamma_level"),
                data.get("call_wall"),
                data.get("put_wall"),
                data.get("spot_price"),
                data.get("total_gamma"),
                data.get("file_size"),
                data.get("quality_score"),
                data.get("data_lag_seconds"),
                data.get("oi_coverage_pct"),
            ),
        )
        rows += 1

        # Batch insert strikes if present
        strikes = data.get("strikes", [])
        if strikes:
            snapshot_id = conn.total_changes  # approximate; use last_insert_rowid
            cursor = await conn.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            snapshot_id = row[0] if row else 0

            strike_rows = [
                (
                    snapshot_id,
                    data.get("symbol", "SPX"),
                    ts,
                    s.get("strike", 0),
                    s.get("call_gex", 0),
                    s.get("put_gex", 0),
                    s.get("call_oi", 0),
                    s.get("put_oi", 0),
                    s.get("call_vol", 0),
                    s.get("put_vol", 0),
                    s.get("net_gex", 0),
                )
                for s in strikes
            ]
            await conn.executemany(
                """INSERT INTO gex_strikes
                   (snapshot_id, symbol, timestamp, strike,
                    call_gex, put_gex, call_oi, put_oi, call_vol, put_vol, net_gex)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                strike_rows,
            )
            rows += len(strike_rows)

        return rows

    # ── VIX writer ─────────────────────────────────────────────────────────────

    async def _write_vix_analysis(self, conn, data: dict, now: str) -> int:
        """Insert VIX term structure analysis row."""
        ts = data.get("_meta", {}).get("fetched_at", now)
        await conn.execute(
            """INSERT INTO vix_analysis
               (timestamp, vix_spot, vx1, vx2, term_structure_ratio,
                term_structure_state, panic_premium)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                data.get("vix_spot"),
                data.get("vx1"),
                data.get("vx2"),
                data.get("term_structure_ratio"),
                data.get("term_structure_state"),
                data.get("panic_premium"),
            ),
        )
        return 1

    # ── Dark pool writer ───────────────────────────────────────────────────────

    async def _write_dark_pool_metrics(self, conn, data: dict, now: str) -> int:
        """Insert or update dark pool metrics for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await conn.execute(
            """INSERT OR REPLACE INTO dark_pool_metrics
               (date, dix_value, chartexchange_short_ratio,
                stockgrid_20d_slope, stockgrid_60d_slope,
                stockgrid_divergence, dbmf_ma5_recovery,
                dix_signal, short_ratio_signal, stockgrid_signal,
                aggregated_signal, v_net, ema_fast_5, ema_slow_20,
                zero_cross_signal, momentum_reversal_signal, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                today,
                data.get("dix_value"),
                data.get("chartexchange_short_ratio"),
                data.get("stockgrid_20d_slope"),
                data.get("stockgrid_60d_slope"),
                data.get("stockgrid_divergence"),
                data.get("dbmf_ma5_recovery"),
                data.get("dix_signal"),
                data.get("short_ratio_signal"),
                data.get("stockgrid_signal"),
                data.get("aggregated_signal"),
                data.get("v_net"),
                data.get("ema_fast_5"),
                data.get("ema_slow_20"),
                data.get("zero_cross_signal"),
                data.get("momentum_reversal_signal"),
                now,
            ),
        )
        return 1

    # ── Crypto derivatives writer ──────────────────────────────────────────────

    async def _write_crypto_derivatives(self, conn, data: dict, now: str) -> int:
        """Insert crypto derivatives snapshot."""
        ts = data.get("_meta", {}).get("fetched_at", now)
        await conn.execute(
            """INSERT OR REPLACE INTO crypto_derivatives
               (timestamp, btc_funding_rate, btc_oi, oi_change_1h,
                liquidation_spike, cryptoquant_elr, funding_anomaly,
                oi_crash, leverage_cleanup)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                data.get("btc_funding_rate", 0),
                data.get("btc_oi"),
                data.get("oi_change_1h"),
                data.get("liquidation_spike"),
                data.get("cryptoquant_elr"),
                data.get("funding_anomaly"),
                data.get("oi_crash"),
                data.get("leverage_cleanup"),
            ),
        )
        return 1

    # ── Validation audit log writer ────────────────────────────────────────────

    async def write_validation_audit(
        self,
        source: str,
        check_type: str,
        check_name: str,
        passed: bool,
        symbol: Optional[str] = None,
        input_value: Optional[str] = None,
        expected_range: Optional[str] = None,
        severity: str = "INFO",
        message: Optional[str] = None,
        raw_data_hash: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """Write a validation audit log entry.

        This resolves the 0-row anomaly for validation_audit_log by ensuring
        every pipeline cycle writes at least one audit entry per source.
        """
        now = datetime.now(timezone.utc).isoformat()
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO validation_audit_log
                   (timestamp, source, symbol, check_type, check_name,
                    passed, input_value, expected_range, severity,
                    message, raw_data_hash, retry_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now,
                    source,
                    symbol,
                    check_type,
                    check_name,
                    passed,
                    input_value,
                    expected_range,
                    severity,
                    message,
                    raw_data_hash,
                    retry_count,
                ),
            )

    # ── Gateway snapshot writer ────────────────────────────────────────────────

    async def write_gateway_snapshot(
        self,
        source: str,
        layer1_output: Optional[dict] = None,
        layer2_output: Optional[dict] = None,
        status: str = "OK",
        error_message: Optional[str] = None,
    ) -> None:
        """Write a gateway snapshot capturing Layer1/Layer2 payloads.

        This resolves the 0-row anomaly for gateway_snapshots by writing
        a snapshot for every pipeline cycle.
        """
        now = datetime.now(timezone.utc).isoformat()
        async with get_db() as conn:
            await self._write_gateway_snapshot(
                conn, source,
                {"layer1": layer1_output, "layer2": layer2_output} if layer1_output or layer2_output else {},
                now, status=status, error_message=error_message,
                layer1_output=layer1_output,
                layer2_output=layer2_output,
            )

    async def _write_gateway_snapshot(
        self,
        conn,
        source: str,
        data: dict,
        now: str,
        status: str = "OK",
        error_message: Optional[str] = None,
        layer1_output: Optional[dict] = None,
        layer2_output: Optional[dict] = None,
    ) -> int:
        """Internal: insert a gateway_snapshots row."""
        payload_json = json.dumps(data, default=str) if data else None
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()[:16] if payload_json else None
        payload_size = len(payload_json) if payload_json else 0

        l1_json = json.dumps(layer1_output, default=str) if layer1_output else None
        l2_json = json.dumps(layer2_output, default=str) if layer2_output else None

        await conn.execute(
            """INSERT INTO gateway_snapshots
               (timestamp, source, payload_hash, payload_size,
                layer1_output, layer2_output, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, source, payload_hash, payload_size, l1_json, l2_json, status, error_message),
        )
        return 1

    # ── Signal alert writer ────────────────────────────────────────────────────

    async def write_signal_alert(
        self,
        total_score: float,
        alert_level: str,
        gex_score: Optional[float] = None,
        vix_score: Optional[float] = None,
        crypto_score: Optional[float] = None,
        darkpool_score: Optional[float] = None,
        hawkes_branching_ratio: Optional[float] = None,
        details: Optional[dict] = None,
    ) -> int:
        """Write a signal alert to the database.

        Returns:
            The row id of the inserted alert.
        """
        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, default=str) if details else None

        async with get_db() as conn:
            cursor = await conn.execute(
                """INSERT INTO signal_alerts
                   (trigger_time, total_score, gex_score, vix_score,
                    crypto_score, darkpool_score, alert_level,
                    hawkes_branching_ratio, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now,
                    total_score,
                    gex_score,
                    vix_score,
                    crypto_score,
                    darkpool_score,
                    alert_level,
                    hawkes_branching_ratio,
                    details_json,
                ),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
