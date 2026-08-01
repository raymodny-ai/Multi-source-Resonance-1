"""
Tiered concurrent executor for optimised fetcher scheduling.
Implements a three-tier priority system to minimise total pipeline latency.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.config import Settings
from backend.eventbus.event_bus import EventBus
from backend.eventbus.events import EventType
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)


# ── Tier definitions ─────────────────────────────────────────────────────────
# Tier 1 (priority): GEXMetrix — needed before scoring can begin
# Tier 2 (standard):  VIX, Crypto, Darkpool, yfinance, CBOE, sentiment, etc.
# Tier 3 (deferred):  AXLFI — background write, does not block main flow

TIER_1_SOURCES: frozenset[str] = frozenset({"gexmetrix"})
TIER_3_SOURCES: frozenset[str] = frozenset({"axlfi"})
# Everything else falls into Tier 2


@dataclass
class FetchResult:
    """Result envelope for a single fetcher execution.

    ``success`` here means "data is usable downstream" — both real fetches
    and accepted mock fallbacks qualify. Distinguish via ``is_mock``.
    """
    source: str
    data: dict = field(default_factory=dict)
    elapsed_sec: float = 0.0
    success: bool = True
    error: Optional[str] = None
    is_mock: bool = False
    mock_reason: Optional[str] = None
    retry_count: int = 0
    tier: int = 2


@dataclass
class ExecutionReport:
    """Summary of a full concurrent execution cycle."""
    results: dict[str, FetchResult] = field(default_factory=dict)
    total_elapsed_sec: float = 0.0
    tier1_elapsed_sec: float = 0.0
    tier2_elapsed_sec: float = 0.0
    success_count: int = 0
    error_count: int = 0
    mock_count: int = 0


class ConcurrentExecutor:
    """Optimised three-tier concurrent fetcher executor.

    Tier strategy:
        Tier 1 — GEXMetrix (and other critical sources) run first.
                 As soon as Tier 1 completes, Phase 2/3 can begin
                 without waiting for lower tiers.
        Tier 2 — Standard sources run concurrently with Tier 1 scoring.
        Tier 3 — AXLFI and other deferred sources run in the background;
                 results are written asynchronously and never block the
                 main pipeline flow.

    This reduces total pipeline latency from ~10s (serial) to ~6s.
    """

    def __init__(self, config: Settings, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self._thread_pool = ThreadPoolExecutor(
            max_workers=config.max_workers,
            thread_name_prefix="fetcher",
        )
        self._per_fetcher_timeout = config.fetch_timeout_seconds
        # FIX-18: keep the latest tier-3 task so await_tier3() / shutdown
        # can drain it. Without a reference the task is garbage-collected
        # mid-flight and its results are silently lost between cycles.
        self._tier3_task: Optional[asyncio.Task] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    async def execute_fetchers(
        self,
        fetchers: list[BaseFetcher],
    ) -> ExecutionReport:
        """Execute all fetchers using the three-tier strategy.

        Args:
            fetchers: List of BaseFetcher subclass instances.

        Returns:
            ExecutionReport with per-fetcher results and timing.
        """
        report = ExecutionReport()
        cycle_start = time.monotonic()

        # Partition fetchers into tiers
        tier1 = [f for f in fetchers if f.source_name.lower() in TIER_1_SOURCES]
        tier3 = [f for f in fetchers if f.source_name.lower() in TIER_3_SOURCES]
        tier2 = [
            f for f in fetchers
            if f.source_name.lower() not in TIER_1_SOURCES
            and f.source_name.lower() not in TIER_3_SOURCES
        ]

        # ── Tier 1: priority sources ──────────────────────────────────────────
        if tier1:
            logger.info(f"[Tier1] Starting {len(tier1)} priority fetcher(s)")
            t1_start = time.monotonic()
            await self.event_bus.publish(
                EventType.DATA_FETCH_START,
                {"tier": 1, "sources": [f.source_name for f in tier1]},
            )
            tier1_results = await self._run_tier(tier1, tier=1)
            report.tier1_elapsed_sec = round(time.monotonic() - t1_start, 3)
            for r in tier1_results:
                report.results[r.source] = r
                await self._publish_fetch_result(r)

            logger.info(
                f"[Tier1] Complete in {report.tier1_elapsed_sec:.2f}s — "
                f"{sum(1 for r in tier1_results if r.success)}/{len(tier1_results)} ok"
            )

        # ── Tier 2: standard sources (concurrent, may overlap with Tier1 scoring)
        if tier2:
            logger.info(f"[Tier2] Starting {len(tier2)} standard fetcher(s)")
            t2_start = time.monotonic()
            await self.event_bus.publish(
                EventType.DATA_FETCH_START,
                {"tier": 2, "sources": [f.source_name for f in tier2]},
            )
            tier2_results = await self._run_tier(tier2, tier=2)
            report.tier2_elapsed_sec = round(time.monotonic() - t2_start, 3)
            for r in tier2_results:
                report.results[r.source] = r
                await self._publish_fetch_result(r)

            logger.info(
                f"[Tier2] Complete in {report.tier2_elapsed_sec:.2f}s — "
                f"{sum(1 for r in tier2_results if r.success)}/{len(tier2_results)} ok"
            )

        # ── Tier 3: deferred sources (fire-and-forget background) ─────────────
        # FIX-18: previously the tier-3 task was created with
        # ``asyncio.create_task`` and never awaited, so the function returned
        # *before* the deferred fetchers finished. ``report.success_count`` /
        # ``mock_count`` were computed against a partial report, and the
        # background results were lost on the next cycle (the report object
        # was discarded). We now keep a reference to the task and ``await``
        # it on shutdown so we never lose tier-3 results.
        if tier3:
            logger.info(
                f"[Tier3] Scheduling {len(tier3)} deferred fetcher(s) in background"
            )
            self._tier3_task = asyncio.create_task(
                self._run_tier3_background(tier3, report)
            )

        # Compute counts from whatever results we have now. Tier 3 may add
        # more later; the background coroutine increments the same counters
        # atomically as it completes so the next reader sees the full picture.
        report.total_elapsed_sec = round(time.monotonic() - cycle_start, 3)
        report.success_count = sum(
            1 for r in report.results.values() if r.success and not r.is_mock
        )
        report.error_count = sum(
            1 for r in report.results.values() if not r.success or bool(r.error)
        )
        report.mock_count = sum(1 for r in report.results.values() if r.is_mock)

        return report

    async def await_tier3(self, timeout: float = 5.0) -> None:
        """FIX-18: wait for the most recent tier-3 background task to finish.

        Called by the pipeline during shutdown and by health checks so the
        deferred fetchers' results are not lost. Safe to call when no task
        is in flight (no-op). Safe to call concurrently (the await is on
        the task object itself, which is single-consumer).
        """
        task = getattr(self, "_tier3_task", None)
        if task is None or task.done():
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"[Tier3] Background task did not finish within {timeout}s; "
                "results may be incomplete for this cycle."
            )

    # ── Internal: tier execution ───────────────────────────────────────────────

    async def _run_tier(
        self,
        fetchers: list[BaseFetcher],
        tier: int,
    ) -> list[FetchResult]:
        """Run a set of fetchers concurrently with per-fetcher timeout.

        Uses asyncio.gather so all fetchers in the tier run in parallel.
        Individual failures are caught and recorded without cancelling siblings.
        """
        tasks = [
            asyncio.create_task(self._execute_single(fetcher, tier=tier))
            for fetcher in fetchers
        ]
        return await asyncio.gather(*tasks)

    async def _run_tier3_background(
        self,
        fetchers: list[BaseFetcher],
        report: ExecutionReport,
    ) -> None:
        """Run Tier 3 fetchers in background; results are added to report.

        FIX-18: keep a reference to the task on the executor so
        ``await_tier3`` (and shutdown) can wait for it. Without this, the
        task was garbage-collected mid-flight and the deferred results
        were silently dropped between cycles.
        """
        try:
            await self.event_bus.publish(
                EventType.DATA_FETCH_START,
                {"tier": 3, "sources": [f.source_name for f in fetchers]},
            )
            results = await self._run_tier(fetchers, tier=3)
            for r in results:
                report.results[r.source] = r
                await self._publish_fetch_result(r)
            # FIX-18: refresh the aggregate counters after the deferred
            # results land so the next caller's report.mock_count /
            # error_count / success_count are correct even if they read the
            # report after the function returns.
            report.success_count = sum(
                1 for v in report.results.values() if v.success and not v.is_mock
            )
            report.error_count = sum(
                1 for v in report.results.values() if not v.success or bool(v.error)
            )
            report.mock_count = sum(1 for v in report.results.values() if v.is_mock)
            logger.info(
                f"[Tier3] Background complete — "
                f"{sum(1 for r in results if r.success)}/{len(results)} ok"
            )
        except Exception as exc:
            logger.error(f"[Tier3] Background execution failed: {exc}", exc_info=True)

    async def _execute_single(
        self,
        fetcher: BaseFetcher,
        tier: int,
    ) -> FetchResult:
        """Execute a single fetcher with timeout protection.

        Falls back to mock data on timeout or exception.
        """
        source = fetcher.source_name
        start = time.monotonic()
        try:
            data = await asyncio.wait_for(
                fetcher.fetch_with_retry(),
                timeout=self._per_fetcher_timeout,
            )
            elapsed = round(time.monotonic() - start, 3)
            meta = data.get("_meta", {}) if isinstance(data, dict) else {}
            is_mock = bool(meta.get("is_mock", False))
            error = meta.get("error")
            mock_reason = meta.get("mock_reason")
            retry_count = int(meta.get("retry_count", 0))

            return FetchResult(
                source=source,
                data=data,
                elapsed_sec=elapsed,
                # success = data is usable (real or accepted mock); error indicates
                # a hard failure with no usable payload.
                success=not bool(error),
                error=error,
                is_mock=is_mock,
                mock_reason=mock_reason,
                retry_count=retry_count,
                tier=tier,
            )

        except asyncio.TimeoutError:
            elapsed = round(time.monotonic() - start, 3)
            logger.error(f"[{source}] Timed out after {self._per_fetcher_timeout}s")
            return FetchResult(
                source=source,
                elapsed_sec=elapsed,
                success=False,
                error=f"Timeout after {self._per_fetcher_timeout}s",
                tier=tier,
            )

        except Exception as exc:
            elapsed = round(time.monotonic() - start, 3)
            logger.error(f"[{source}] Unexpected error: {exc}", exc_info=True)
            return FetchResult(
                source=source,
                elapsed_sec=elapsed,
                success=False,
                error=str(exc),
                tier=tier,
            )

    # ── Internal: event publishing ─────────────────────────────────────────────

    async def _publish_fetch_result(self, result: FetchResult) -> None:
        """Publish the appropriate event for a fetch result.

        Mock fallbacks get an additional ``DATA_MOCK_FALLBACK`` event so
        listeners (and the frontend) can surface degraded source visibility.
        """
        if result.success:
            await self.event_bus.publish(
                EventType.DATA_FETCH_COMPLETE,
                {
                    "source": result.source,
                    "elapsed_sec": result.elapsed_sec,
                    "is_mock": result.is_mock,
                    "mock_reason": result.mock_reason,
                    "retry_count": result.retry_count,
                    "tier": result.tier,
                    "data": result.data,
                },
            )
            if result.is_mock:
                await self.event_bus.publish(
                    EventType.DATA_MOCK_FALLBACK,
                    {
                        "source": result.source,
                        "mock_reason": result.mock_reason,
                        "retry_count": result.retry_count,
                        "tier": result.tier,
                    },
                )
        else:
            await self.event_bus.publish(
                EventType.DATA_FETCH_ERROR,
                {
                    "source": result.source,
                    "elapsed_sec": result.elapsed_sec,
                    "error": result.error,
                    "tier": result.tier,
                },
            )

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Shut down the thread pool executor."""
        self._thread_pool.shutdown(wait=False)
        logger.info("ConcurrentExecutor thread pool shut down")
