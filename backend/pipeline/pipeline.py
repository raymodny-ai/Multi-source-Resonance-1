"""
Pipeline V2.0 — Three-phase data collection and scoring pipeline.

Phases:
    Phase 1: Data Collection — concurrent fetchers via ConcurrentExecutor
    Phase 2: Quantitative Analysis — call quant analyzers on fetched data
    Phase 3: Signal Scoring — compute resonance scores and generate alerts
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from backend.config import Settings
from backend.eventbus.event_bus import EventBus
from backend.eventbus.events import EventType
from backend.fetchers.base import BaseFetcher
from backend.pipeline.concurrent_executor import ConcurrentExecutor, ExecutionReport
from backend.pipeline.data_writer import DataWriter

logger = logging.getLogger(__name__)


class Pipeline:
    """Three-phase pipeline: Collect → Analyse → Score.

    The pipeline is decoupled via EventBus:
        - Phase 1 publishes DATA_FETCH_COMPLETE events as each fetcher finishes
        - Phase 2 subscribes to analysis events and publishes ANALYSIS_COMPLETE
        - Phase 3 subscribes to scoring events and writes final results

    Usage:
        pipeline = Pipeline(config, event_bus, fetchers)
        await pipeline.start()   # starts periodic collection loop
        await pipeline.stop()    # graceful shutdown
    """

    # Alert level thresholds on the NORMALIZED 0-100 scale.
    # The resonance scorer (backend/quant/scoring.py) returns total_score as a
    # normalized 0-100 value; _basic_score below also emits a normalized total.
    # (Matches scoring.LEVEL_THRESHOLDS: LEVEL_1 25-50 / LEVEL_2 50-75 / LEVEL_3 75+)
    LEVEL_THRESHOLDS = {
        "LEVEL_1": 25.0,
        "LEVEL_2": 50.0,
        "LEVEL_3": 75.0,
    }

    def __init__(
        self,
        config: Settings,
        event_bus: EventBus,
        fetchers: Optional[list[BaseFetcher]] = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.fetchers: list[BaseFetcher] = fetchers or []
        self.executor = ConcurrentExecutor(config, event_bus)
        self.writer = DataWriter()

        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._last_cycle_report: Optional[dict] = None
        # FIX-27: writing flag — jobs that conflict with ongoing writes
        # (VACUUM, archive, backup) can poll this and skip their run.
        self._is_writing: bool = False
        self._write_lock = asyncio.Lock()

        # Quant analyzers registry (populated externally to avoid import conflicts)
        # Key: source_name, Value: async callable(data: dict) -> dict
        self._analyzers: dict[str, Any] = {}

        # Scoring function (injected to avoid hard dependency on quant module)
        # Signature: async callable(analysis_results: dict) -> dict
        self._scorer: Optional[Any] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the periodic pipeline loop.

        Runs indefinitely until stop() is called. Each cycle waits
        fetch_interval_seconds before starting the next cycle.
        """
        if self._running:
            logger.warning("Pipeline already running")
            return

        self._running = True
        await self.event_bus.publish(EventType.SYSTEM_START, {
            "component": "pipeline",
            "fetchers": len(self.fetchers),
            "interval_sec": self.config.fetch_interval_seconds,
        })
        logger.info(
            f"Pipeline started — {len(self.fetchers)} fetcher(s), "
            f"interval={self.config.fetch_interval_seconds}s"
        )

        try:
            while self._running:
                cycle_start = time.monotonic()
                self._cycle_count += 1
                logger.info(f"=== Pipeline cycle {self._cycle_count} starting ===")

                try:
                    report = await self.run_cycle()
                    self._last_cycle_report = report
                    elapsed = round(time.monotonic() - cycle_start, 2)
                    logger.info(
                        f"=== Pipeline cycle {self._cycle_count} complete "
                        f"in {elapsed}s — "
                        f"success={report.get('success_count', 0)}, "
                        f"errors={report.get('error_count', 0)} ==="
                    )
                except Exception as exc:
                    logger.error(
                        f"Pipeline cycle {self._cycle_count} failed: {exc}",
                        exc_info=True,
                    )

                # Wait for next interval
                if self._running:
                    await asyncio.sleep(self.config.fetch_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Pipeline loop cancelled")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the pipeline loop gracefully."""
        logger.info("Stopping pipeline...")
        self._running = False
        # FIX-18: drain the in-flight tier-3 background task so we don't
        # lose the deferred fetchers' results mid-shutdown.
        try:
            await self.executor.await_tier3(timeout=10.0)
        except Exception as exc:
            logger.warning(f"Pipeline.stop: tier-3 drain failed: {exc}")
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.executor.shutdown()
        await self.event_bus.publish(EventType.SYSTEM_STOP, {"component": "pipeline"})
        logger.info("Pipeline stopped")

    def start_background(self) -> asyncio.Task:
        """Start the pipeline as a background asyncio task.

        Returns:
            The asyncio.Task handle (for cancellation / awaiting).
        """
        self._task = asyncio.create_task(self.start(), name="pipeline-loop")
        return self._task

    # ── Core cycle ─────────────────────────────────────────────────────────────

    async def run_cycle(self) -> dict:
        """Execute one full Collect → Analyse → Score cycle.

        Returns:
            Dict summarising the cycle results.
        """
        cycle_ts = datetime.now(timezone.utc).isoformat()

        # ── Phase 1: Data Collection ───────────────────────────────────────────
        logger.info("[Phase 1] Data collection starting")
        exec_report = await self._phase1_collect()
        collected_data = {
            name: r.data
            for name, r in exec_report.results.items()
            if r.success
        }

        # ── Phase 2: Quantitative Analysis ─────────────────────────────────────
        logger.info("[Phase 2] Quantitative analysis starting")
        analysis_results = await self._phase2_analyse(collected_data)

        # ── Phase 3: Signal Scoring ────────────────────────────────────────────
        logger.info("[Phase 3] Signal scoring starting")
        scoring_result = await self._phase3_score(analysis_results)

        # ── Persist results ────────────────────────────────────────────────────
        write_results = await self._persist(collected_data, analysis_results, scoring_result)

        # Per-source breakdown consumed by API/UI for status & mock-source surfacing.
        source_details = [
            {
                "source": r.source,
                "tier": r.tier,
                "success": r.success,
                "is_mock": r.is_mock,
                "mock_reason": r.mock_reason,
                "retry_count": r.retry_count,
                "elapsed_sec": r.elapsed_sec,
                "error": r.error,
            }
            for r in exec_report.results.values()
        ]

        result = {
            "cycle_ts": cycle_ts,
            "cycle_number": self._cycle_count,
            "total_elapsed_sec": exec_report.total_elapsed_sec,
            "success_count": exec_report.success_count,
            "error_count": exec_report.error_count,
            "mock_count": exec_report.mock_count,
            "tier1_elapsed_sec": exec_report.tier1_elapsed_sec,
            "tier2_elapsed_sec": exec_report.tier2_elapsed_sec,
            "analysis_count": len(analysis_results),
            "scoring": scoring_result,
            "source_details": source_details,
            "write_results": write_results,
        }

        await self.event_bus.publish(
            EventType.PIPELINE_CYCLE_COMPLETE,
            {
                "cycle_ts": cycle_ts,
                "cycle_number": self._cycle_count,
                "success_count": exec_report.success_count,
                "error_count": exec_report.error_count,
                "mock_count": exec_report.mock_count,
            },
        )

        return result

    # ── Phase 1: Collect ───────────────────────────────────────────────────────

    async def _phase1_collect(self) -> ExecutionReport:
        """Run all fetchers through the concurrent executor."""
        return await self.executor.execute_fetchers(self.fetchers)

    # ── Phase 2: Analyse ───────────────────────────────────────────────────────

    async def _phase2_analyse(self, collected_data: dict[str, dict]) -> dict[str, dict]:
        """Run quant analyzers on collected data.

        Each registered analyzer is called with the corresponding source data.
        Analyzers run concurrently via asyncio.gather.
        """
        await self.event_bus.publish(EventType.ANALYSIS_START, {
            "sources": list(collected_data.keys()),
        })

        results: dict[str, dict] = {}

        if not self._analyzers:
            # No analyzers registered yet — pass data through as-is
            logger.info("[Phase 2] No analyzers registered — passing raw data")
            results = {k: {"raw": v} for k, v in collected_data.items()}
        else:
            tasks = {}
            for source, data in collected_data.items():
                analyzer = self._analyzers.get(source)
                if analyzer:
                    tasks[source] = asyncio.create_task(
                        self._safe_analyze(source, analyzer, data)
                    )
                else:
                    # No analyzer for this source — pass through
                    results[source] = {"raw": data}

            if tasks:
                completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for source, result in zip(tasks.keys(), completed):
                    if isinstance(result, Exception):
                        logger.error(f"[Phase 2] Analyzer '{source}' failed: {result}")
                        results[source] = {"error": str(result)}
                    else:
                        results[source] = result

        await self.event_bus.publish(EventType.ANALYSIS_COMPLETE, {
            "results": {k: list(v.keys()) for k, v in results.items()},
        })
        return results

    async def _safe_analyze(
        self,
        source: str,
        analyzer,
        data: dict,
    ) -> dict:
        """Invoke an analyzer with error handling."""
        try:
            return await analyzer(data)
        except Exception as exc:
            logger.error(f"[Phase 2] Analyzer '{source}' raised: {exc}", exc_info=True)
            return {"error": str(exc)}

    # ── Phase 3: Score ─────────────────────────────────────────────────────────

    async def _phase3_score(self, analysis_results: dict[str, dict]) -> dict:
        """Compute resonance scores from analysis results.

        If a scorer is registered, delegate to it. Otherwise compute a
        basic score from available dimension data.
        """
        await self.event_bus.publish(EventType.SCORING_START, {
            "analysis_count": len(analysis_results),
        })

        scoring_result: dict = {}

        if self._scorer:
            try:
                scoring_result = await self._scorer(analysis_results)
            except Exception as exc:
                logger.error(f"[Phase 3] Scorer failed: {exc}", exc_info=True)
                scoring_result = {"error": str(exc)}
        else:
            # Basic scoring fallback when quant module not yet available
            scoring_result = self._basic_score(analysis_results)

        # Determine alert level
        total_score = scoring_result.get("total_score", 0.0)
        alert_level = self._compute_alert_level(total_score)
        scoring_result["alert_level"] = alert_level

        # ── Bayesian weight update (post-scoring) ────────────────────────────
        await self._update_bayesian_weights(scoring_result)

        await self.event_bus.publish(EventType.SCORING_COMPLETE, scoring_result)
        await self.event_bus.publish(EventType.SIGNAL_GENERATED, scoring_result)

        # Publish alert event if LEVEL_2+
        if alert_level in ("LEVEL_2", "LEVEL_3"):
            await self.event_bus.publish(EventType.SIGNAL_ALERT, {
                "total_score": total_score,
                "alert_level": alert_level,
                "details": scoring_result,
            })
            logger.info(
                f"[Phase 3] ALERT: {alert_level} — score={total_score:.2f}"
            )

        return scoring_result

    def _basic_score(self, analysis_results: dict[str, dict]) -> dict:
        """Compute a basic resonance score when quant scorer is not available.

        This is a placeholder that sums any pre-computed dimension scores
        found in the analysis results.
        """
        gex_score = 0.0
        vix_score = 0.0
        crypto_score = 0.0
        darkpool_score = 0.0

        for source, result in analysis_results.items():
            src_lower = source.lower()
            if "gex" in src_lower:
                gex_score = result.get("gex_score", 0.0) or 0.0
            elif "vix" in src_lower or "cboe" in src_lower:
                vix_score = result.get("vix_score", 0.0) or 0.0
            elif "crypto" in src_lower:
                crypto_score = result.get("crypto_score", 0.0) or 0.0
            elif "dark" in src_lower or "pool" in src_lower:
                darkpool_score = result.get("darkpool_score", 0.0) or 0.0

        # Normalize: each dimension is 0-100; sum and cap at 100 to stay on the
        # normalized scale the alert thresholds expect. More dimensions firing
        # pushes the total up (resonance), but it never exceeds 100.
        total = min(gex_score + vix_score + crypto_score + darkpool_score, 100.0)
        return {
            "total_score": round(total, 2),
            "gex_score": gex_score,
            "vix_score": vix_score,
            "crypto_score": crypto_score,
            "darkpool_score": darkpool_score,
            "scorer": "basic_fallback",
        }

    def _compute_alert_level(self, total_score: float) -> str:
        """Map a total score to an alert level string."""
        if total_score >= self.LEVEL_THRESHOLDS["LEVEL_3"]:
            return "LEVEL_3"
        elif total_score >= self.LEVEL_THRESHOLDS["LEVEL_2"]:
            return "LEVEL_2"
        elif total_score >= self.LEVEL_THRESHOLDS["LEVEL_1"]:
            return "LEVEL_1"
        return "NONE"

    # ── Bayesian weight update ────────────────────────────────────────────────

    async def _update_bayesian_weights(self, scoring_result: dict) -> None:
        """After scoring, feed latest signal outcome into BayesianWeightAdapter.

        This is a lightweight best-effort update: if the adapter or database
        is unavailable the error is logged but does not break the pipeline.
        """
        try:
            from backend.quant.bayesian_weights import BayesianWeightAdapter
            from backend.quant.scoring import _get_adapter
            from backend.database import get_db

            adapter = _get_adapter()

            # Fetch the most recent evaluated signal outcome from the DB
            async with get_db() as db:
                cursor = await db.execute("""
                    SELECT gex_score, vix_score, crypto_score, darkpool_score,
                           forward_return, trigger_time, alert_level
                    FROM signal_alerts
                    WHERE outcome IS NOT NULL
                    ORDER BY outcome_checked_at DESC
                    LIMIT 1
                """)
                row = await cursor.fetchone()

            if row is None:
                return  # No evaluated outcomes yet

            outcome_dict = {
                "gex_score": row["gex_score"] or 0.0,
                "vix_score": row["vix_score"] or 0.0,
                "crypto_score": row["crypto_score"] or 0.0,
                "darkpool_score": row["darkpool_score"] or 0.0,
                "forward_return": row["forward_return"] or 0.0,
                "trigger_time": row["trigger_time"],
                "alert_level": row["alert_level"] or "LEVEL_0",
            }

            # Single-outcome incremental update (min_outcomes=1 for incremental)
            # The adapter's internal decay + Bayesian update handles smoothing.
            prev_weights = adapter.get_current_weights()
            new_weights = adapter.update_weights([outcome_dict])

            if new_weights != prev_weights:
                logger.info(
                    f"[Phase 3] Bayesian weights updated: {new_weights}"
                )

        except Exception as exc:
            logger.warning(
                f"[Phase 3] Bayesian weight update skipped: {exc}"
            )

    # ── Hawkes branching ratio ────────────────────────────────────────────────

    async def _compute_hawkes_branching_ratio(self) -> Optional[float]:
        """Compute the Hawkes self-excitation branching ratio from recent alerts.

        Uses the timestamps of recent signal alerts as event times, fits the
        AR(1) approximation (lambda_t = a + b*lambda_{t-1}) and returns the
        branching ratio b in [0,1]. This measures how strongly each signal
        triggers follow-up signals. Was previously never wired into the
        pipeline, so hawkes_branching_ratio was always NULL in the DB.

        Returns None when there are too few events (<3) to fit.
        """
        try:
            from backend.database import get_db
            from backend.quant.hawkes_model import analyze as hawkes_analyze
            import datetime as _dt

            async with get_db() as db:
                cursor = await db.execute("""
                    SELECT trigger_time FROM signal_alerts
                    ORDER BY id DESC LIMIT 60
                """)
                rows = await cursor.fetchall()

            if not rows or len(rows) < 3:
                return None

            # Convert ISO trigger times to epoch seconds (floats) as event times
            event_times = []
            now = time.time()
            for r in rows:
                ts = r["trigger_time"]
                try:
                    dt = _dt.datetime.fromisoformat(
                        ts.replace("Z", "+00:00")
                    ).astimezone(_dt.timezone.utc)
                    event_times.append(dt.timestamp())
                except Exception:
                    continue

            if len(event_times) < 3:
                return None

            # Fit on most recent events; keep time values relative (latest first)
            result = await hawkes_analyze({"event_times": sorted(event_times)})
            br = result.get("branching_ratio")
            return float(br) if br is not None else None
        except Exception as exc:
            logger.warning(f"[Persist] Hawkes BR computation failed: {exc}")
            return None

    # ── Persistence ────────────────────────────────────────────────────────────

    async def _persist(
        self,
        collected_data: dict[str, dict],
        analysis_results: dict[str, dict],
        scoring_result: dict,
    ) -> dict[str, dict]:
        """Write all results to the database. Returns write results keyed by source.

        FIX-27: held under ``_write_lock`` so concurrent scheduler jobs
        (VACUUM, archive, backup) can observe ``is_writing`` and skip
        their run instead of racing the pipeline.
        """
        write_results: dict[str, dict] = {}
        async with self._write_lock:
            self._is_writing = True
        try:
            try:
                # Write fetcher data
                write_results = await self.writer.write_fetch_results(collected_data)
                logger.debug(f"[Persist] Fetcher data written: {write_results}")

                # Write validation audit entries (resolve 0-row anomaly)
                for source in collected_data:
                    await self.writer.write_validation_audit(
                        source=source,
                        check_type="pipeline_integrity",
                        check_name="data_collected",
                        passed=True,
                        message=f"Pipeline cycle {self._cycle_count}: data collected successfully",
                    )

                # Write gateway snapshot
                await self.writer.write_gateway_snapshot(
                    source="pipeline_cycle",
                    layer1_output={"collected_sources": list(collected_data.keys())},
                    layer2_output=scoring_result,
                    status="OK",
                )

                # Write signal alert if applicable
                alert_level = scoring_result.get("alert_level", "NONE")
                if alert_level != "NONE":
                    hawkes_br = await self._compute_hawkes_branching_ratio()
                    await self.writer.write_signal_alert(
                        total_score=scoring_result.get("total_score", 0.0),
                        alert_level=alert_level,
                        gex_score=scoring_result.get("gex_score"),
                        vix_score=scoring_result.get("vix_score"),
                        crypto_score=scoring_result.get("crypto_score"),
                        darkpool_score=scoring_result.get("darkpool_score"),
                        hawkes_branching_ratio=hawkes_br,
                        details=scoring_result,
                    )
                    logger.info(f"[Persist] Signal alert written: {alert_level} (hawkes={hawkes_br})")

            except Exception as exc:
                logger.error(f"[Persist] Persistence failed: {exc}", exc_info=True)
        finally:
            async with self._write_lock:
                self._is_writing = False

        return write_results

    @property
    def is_writing(self) -> bool:
        """FIX-27: True while ``_persist()`` is in flight."""
        return self._is_writing

    # ── Registration API ───────────────────────────────────────────────────────

    def register_analyzer(self, source_name: str, analyzer) -> None:
        """Register a quant analyzer for a specific data source.

        Args:
            source_name: The fetcher source_name this analyzer handles.
            analyzer: Async callable(data: dict) -> dict with analysis results.
        """
        self._analyzers[source_name] = analyzer
        logger.info(f"Registered analyzer for source '{source_name}'")

    def register_scorer(self, scorer) -> None:
        """Register the resonance scoring function.

        Args:
            scorer: Async callable(analysis_results: dict) -> dict with scores.
        """
        self._scorer = scorer
        logger.info("Registered pipeline scorer")

    # ── Diagnostics ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def last_report(self) -> Optional[dict]:
        return self._last_cycle_report

    def get_status(self) -> dict:
        """Return pipeline status for diagnostics."""
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "fetcher_count": len(self.fetchers),
            "analyzer_count": len(self._analyzers),
            "has_scorer": self._scorer is not None,
            "last_report": self._last_cycle_report,
        }
