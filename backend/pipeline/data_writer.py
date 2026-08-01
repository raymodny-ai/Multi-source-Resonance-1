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

    async def write_fetch_results(self, results: dict[str, dict]) -> dict[str, dict]:
        """Write collected fetcher data to the appropriate domain tables.

        Args:
            results: Mapping of source_name -> fetched data dict. Each dict
                may include ``_meta`` with ``is_mock`` and ``mock_reason``
                keys (FIX-01: mock full-chain tracking).

        Returns:
            Dict mapping source_name -> {"count": int, "error": Optional[str]}.
        """
        written: dict[str, dict] = {}
        now = datetime.now(timezone.utc).isoformat()

        async with get_db() as conn:
            for source, data in results.items():
                try:
                    # FIX-01: extract mock markers from _meta so they persist to DB
                    meta = (data or {}).get("_meta") or {}
                    is_mock = bool(meta.get("is_mock", False))
                    mock_reason = meta.get("mock_reason")
                    count = await self._write_source_data(
                        conn, source, data, now,
                        is_mock=is_mock, mock_reason=mock_reason,
                    )
                    written[source] = {"count": count, "error": None}
                    logger.debug(
                        f"Written {count} row(s) for source '{source}'"
                        f"{' [MOCK]' if is_mock else ''}"
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to write data for '{source}': {exc}",
                        exc_info=True,
                    )
                    written[source] = {"count": 0, "error": str(exc)}

        return written

    async def _write_source_data(
        self,
        conn,
        source: str,
        data: dict,
        now: str,
        is_mock: bool = False,
        mock_reason: Optional[str] = None,
    ) -> int:
        """Route a single source's data to the correct table(s)."""
        source_lower = source.lower()

        if source_lower == "gexmetrix":
            return await self._write_gex_snapshot(conn, data, now, is_mock, mock_reason)
        elif source_lower in ("vix", "cboe"):
            return await self._write_vix_analysis(conn, data, now, is_mock, mock_reason)
        elif source_lower in ("darkpool", "dark_pool_metrics"):
            return await self._write_dark_pool_metrics(conn, data, now, is_mock, mock_reason)
        elif source_lower in ("crypto", "crypto_derivatives"):
            return await self._write_crypto_derivatives(conn, data, now, is_mock, mock_reason)
        elif source_lower in ("options_greeks", "options_chain"):
            return await self._write_options_greeks(conn, data, now)
        else:
            # Generic: write to gateway_snapshots as audit trail
            return await self._write_gateway_snapshot(
                conn, source, data, now, status="OK"
            )

    # ── GEX snapshot writer ────────────────────────────────────────────────────

    async def _write_gex_snapshot(
        self, conn, data: dict, now: str,
        is_mock: bool = False, mock_reason: Optional[str] = None,
    ) -> int:
        """Insert GEX snapshot(s) and associated strikes (batch).

        Supports two shapes (gexmetrix_fetcher returns the multi-symbol form):
        1. Multi-symbol: `{"snapshots": [{symbol, net_gex, ...}, ...], "strikes": [...]}`
        2. Single-snapshot: `{symbol, net_gex, ...}` (legacy single-source fallback)
        """
        rows = 0
        ts = data.get("_meta", {}).get("fetched_at", now)

        # Normalize to list of snapshots
        snapshots = data.get("snapshots")
        if not snapshots:
            # Fall back to single-snapshot shape
            snapshots = [data]

        # Batch insert per-symbol strikes keyed by (snapshot_id, symbol)
        all_strikes_by_symbol: dict[str, list] = {}
        strikes = data.get("strikes")
        if strikes:
            for s in strikes:
                sym = s.get("symbol", "UNKNOWN")
                all_strikes_by_symbol.setdefault(sym, []).append(s)

        for snap in snapshots:
            symbol = snap.get("symbol", "SPX")
            # Insert snapshot summary
            await conn.execute(
                """INSERT INTO gex_snapshots
                   (symbol, timestamp, filename, net_gex, call_gex, put_gex,
                    zero_gamma_level, call_wall, put_wall, spot_price,
                    total_gamma, file_size, quality_score, data_lag_seconds,
                    oi_coverage_pct, is_mock, mock_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    symbol,
                    ts,
                    snap.get("filename", "unknown"),
                    snap.get("net_gex"),
                    snap.get("call_gex"),
                    snap.get("put_gex"),
                    snap.get("zero_gamma_level"),
                    snap.get("call_wall"),
                    snap.get("put_wall"),
                    snap.get("spot_price"),
                    snap.get("total_gamma"),
                    snap.get("file_size"),
                    snap.get("quality_score"),
                    snap.get("data_lag_seconds"),
                    snap.get("oi_coverage_pct"),
                    1 if is_mock else 0,
                    mock_reason,
                ),
            )
            rows += 1

            # Insert strikes for this symbol only
            cursor = await conn.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            snapshot_id = row[0] if row else 0

            sym_strikes = all_strikes_by_symbol.get(symbol, [])
            if sym_strikes:
                strike_rows = [
                    (
                        snapshot_id,
                        symbol,
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
                    for s in sym_strikes
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

    async def _write_vix_analysis(
        self, conn, data: dict, now: str,
        is_mock: bool = False, mock_reason: Optional[str] = None,
    ) -> int:
        """Insert VIX term structure analysis row."""
        ts = data.get("_meta", {}).get("fetched_at", now)
        await conn.execute(
            """INSERT INTO vix_analysis
               (timestamp, vix_spot, vx1, vx2, term_structure_ratio,
                term_structure_state, panic_premium, is_mock, mock_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                data.get("vix_spot"),
                data.get("vx1"),
                data.get("vx2"),
                data.get("term_structure_ratio"),
                data.get("term_structure_state"),
                data.get("panic_premium"),
                1 if is_mock else 0,
                mock_reason,
            ),
        )

        # Also write daily term structure history (date PK) if 'date' provided
        # FRED VIXCLS+VXVCLS source populates this table
        if data.get("date"):
            await conn.execute(
                """INSERT OR REPLACE INTO vix_term_structure
                   (date, vix_spot, vx_3m_proxy, term_structure_ratio,
                    term_structure_state, panic_premium, regime, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    data["date"],
                    data.get("vix_spot"),
                    data.get("vx_3m_proxy"),
                    data.get("term_structure_ratio"),
                    data.get("term_structure_state"),
                    data.get("panic_premium"),
                    data.get("regime"),
                ),
            )
            return 2
        return 1

    # ── Dark pool writer ───────────────────────────────────────────────────────

    async def _write_dark_pool_metrics(
        self, conn, data: dict, now: str,
        is_mock: bool = False, mock_reason: Optional[str] = None,
    ) -> int:
        """Insert or update dark pool metrics for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await conn.execute(
            """INSERT OR REPLACE INTO dark_pool_metrics
               (date, dix_value, chartexchange_short_ratio,
                stockgrid_20d_slope, stockgrid_60d_slope,
                stockgrid_divergence, dbmf_ma5_recovery,
                dix_signal, short_ratio_signal, stockgrid_signal,
                aggregated_signal, v_net, ema_fast_5, ema_slow_20,
                zero_cross_signal, momentum_reversal_signal, updated_at,
                is_mock, mock_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                1 if is_mock else 0,
                mock_reason,
            ),
        )

        # Also write intraday history (no PK — multi-row per day)
        # If 'history' list provided (from SqueezeMetrics CSV last N days), batch insert
        history = data.get("history")
        if history and isinstance(history, list):
            await conn.executemany(
                """INSERT INTO dark_pool_history
                   (date, timestamp, dix_value, gex_value, spx_price,
                    chartexchange_short_ratio, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(h.get("date"), h.get("timestamp"), h.get("dix_value"),
                  h.get("gex_value"), h.get("spx_price"),
                  h.get("chartexchange_short_ratio"), h.get("source", "squeezemetrics"))
                 for h in history],
            )
            return 1 + len(history)
        return 1

    # ── Crypto derivatives writer ──────────────────────────────────────────────

    async def _write_crypto_derivatives(
        self, conn, data: dict, now: str,
        is_mock: bool = False, mock_reason: Optional[str] = None,
    ) -> int:
        """Insert crypto derivatives snapshot."""
        ts = data.get("_meta", {}).get("fetched_at", now)
        await conn.execute(
            """INSERT OR REPLACE INTO crypto_derivatives
               (timestamp, btc_funding_rate, btc_oi, oi_change_1h,
                liquidation_spike, cryptoquant_elr, funding_anomaly,
                oi_crash, leverage_cleanup,
                btc_price, btc_24h_change, btc_volume, eth_price, eth_24h_change,
                is_mock, mock_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                data.get("btc_price"),
                data.get("btc_24h_change"),
                data.get("btc_volume"),
                data.get("eth_price"),
                data.get("eth_24h_change"),
                1 if is_mock else 0,
                mock_reason,
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

    async def _write_options_greeks(self, conn, data: dict, now: str) -> int:
        """Insert options_greeks snapshot per symbol + per-strike detail rows.

        data format (from OptionsChainGreeksFetcher):
            {
              "fetch_timestamp": ISO,
              "symbols": {
                "SPY": {
                  "spot": 740.86,
                  "expiry": "2026-08-28",
                  "days_to_expiry": 30,
                  "calls_count": 125,
                  "puts_count": 132,
                  "atm_iv": 0.18,
                  "atm_strike": 740.0,
                  "atm_delta_call": 0.5452,
                  "atm_delta_put": -0.4548,
                  "atm_gamma": 0.0093,
                  "atm_vega": 0.84,
                  "atm_theta": -0.33,
                  "risk_free_rate": 0.045,
                  "strikes": [
                    {"strike": 530.0, "call_delta": 0.99, "put_delta": -0.01,
                     "gamma": 0.0001, "vega": 0.05, "theta": -0.05,
                     "iv": 0.67, "call_oi": 1, "put_oi": 0},
                    ...
                  ]
                },
                ...
              }
            }
        """
        symbols = data.get("symbols", {})
        if not symbols:
            return 0
        written = 0
        for symbol, payload in symbols.items():
            try:
                cursor = await conn.execute(
                    """
                    INSERT OR REPLACE INTO options_greeks (
                        symbol, timestamp, spot_price, expiry, days_to_expiry,
                        atm_strike, atm_iv, atm_delta_call, atm_delta_put,
                        atm_gamma, atm_vega, atm_theta, risk_free_rate,
                        calls_count, puts_count, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        data.get("fetch_timestamp", now),
                        payload.get("spot"),
                        payload.get("expiry"),
                        payload.get("days_to_expiry"),
                        payload.get("atm_strike"),
                        payload.get("atm_iv"),
                        payload.get("atm_delta_call"),
                        payload.get("atm_delta_put"),
                        payload.get("atm_gamma"),
                        payload.get("atm_vega"),
                        payload.get("atm_theta"),
                        payload.get("risk_free_rate"),
                        payload.get("calls_count"),
                        payload.get("puts_count"),
                        "yfinance",
                    ),
                )
                snap_id = cursor.lastrowid

                # Wipe old strikes for this snapshot, insert fresh
                await conn.execute(
                    "DELETE FROM options_greeks_strikes WHERE snapshot_id = ?",
                    (snap_id,),
                )
                strikes = payload.get("strikes", [])
                if strikes:
                    await conn.executemany(
                        """
                        INSERT INTO options_greeks_strikes (
                            snapshot_id, strike, call_delta, put_delta,
                            gamma, vega, theta, iv, call_oi, put_oi
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                snap_id,
                                s["strike"],
                                s.get("call_delta"),
                                s.get("put_delta"),
                                s.get("gamma"),
                                s.get("vega"),
                                s.get("theta"),
                                s.get("iv"),
                                s.get("call_oi", 0),
                                s.get("put_oi", 0),
                            )
                            for s in strikes
                        ],
                    )
                written += 1
            except Exception as exc:
                logger.warning(f"[options_greeks] Failed to write {symbol}: {exc}")
        # FIX-07: do not commit here; let the outer get_db() context manager
        # handle commit/rollback for full atomicity across multi-source writes.
        return written

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
        mock_sources: Optional[list[str]] = None,
        mock_count: int = 0,
    ) -> int:
        """Write a signal alert to the database.

        Args:
            mock_sources: List of dimension names whose data was mock at signal time.
            mock_count: Number of mock sources used.

        Returns:
            The row id of the inserted alert.
        """
        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, default=str) if details else None
        mock_sources_json = json.dumps(mock_sources) if mock_sources else None

        async with get_db() as conn:
            cursor = await conn.execute(
                """INSERT INTO signal_alerts
                   (trigger_time, total_score, gex_score, vix_score,
                    crypto_score, darkpool_score, alert_level,
                    hawkes_branching_ratio, details,
                    mock_sources, mock_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    mock_sources_json,
                    mock_count,
                ),
            )
            # FIX-20: INSERT has no result set; use lastrowid instead of fetchone()
            return cursor.lastrowid or 0
