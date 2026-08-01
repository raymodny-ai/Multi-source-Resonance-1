"""
Scheduled task manager using APScheduler.
Registers periodic maintenance jobs and integrates with FastAPI lifespan.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.utils.db_maintenance import (
    archive_old_data,
    backup_database_full,
    backup_database_incremental,
    vacuum_and_analyze,
    verify_write_paths,
)
from backend.quant.signal_outcomes import SignalOutcomeTracker
from backend.database import get_db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Scheduler instance
# ─────────────────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(timezone="UTC")

# FIX-27: the scheduler runs independently of the FastAPI app, so we
# can't simply read ``app.state.pipeline`` from inside a job function.
# main.py calls ``set_active_pipeline(pipeline)`` after start_scheduler();
# jobs then call ``_get_active_pipeline()`` to check ``is_writing``. The
# reference is intentionally a weakref so the scheduler never extends
# the pipeline's lifetime.
from typing import Optional
import weakref as _weakref
_active_pipeline_ref: "_weakref.ref | None" = None


def set_active_pipeline(pipeline) -> None:
    """Register the running Pipeline instance for ``is_writing`` checks.

    Called from ``main.py`` lifespan startup after the pipeline is created.
    """
    global _active_pipeline_ref
    _active_pipeline_ref = _weakref.ref(pipeline)


def _get_active_pipeline():
    obj = _active_pipeline_ref() if _active_pipeline_ref is not None else None
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# Job wrappers (APScheduler calls these as async functions)
# ─────────────────────────────────────────────────────────────────────────────

async def job_verify_write_paths():
    """Hourly job: verify that validation_audit_log and gateway_snapshots have writers."""
    logger.info("Scheduled job: verify_write_paths")
    result = await verify_write_paths()
    logger.debug(f"verify_write_paths result: {result}")


async def job_vacuum_analyze():
    """Daily 02:00 UTC: VACUUM + ANALYZE the database.

    FIX-27: skip the run if the pipeline is currently writing — VACUUM
    acquires an exclusive lock and would block the pipeline mid-cycle.
    """
    logger.info("Scheduled job: vacuum_and_analyze")
    pipeline = _get_active_pipeline()
    if pipeline is not None and pipeline.is_writing:
        logger.info("vacuum_and_analyze: pipeline writing, skipping")
        return
    result = await vacuum_and_analyze()
    logger.info(f"vacuum_and_analyze result: {result}")


async def job_archive_old_data():
    """Daily 03:00 UTC: Archive gex_strikes data older than 180 days.

    FIX-27: skip if pipeline writing.
    """
    logger.info("Scheduled job: archive_old_data")
    pipeline = _get_active_pipeline()
    if pipeline is not None and pipeline.is_writing:
        logger.info("archive_old_data: pipeline writing, skipping")
        return
    result = await archive_old_data(days=180)
    logger.info(f"archive_old_data result: {result}")


async def job_incremental_backup():
    """Daily 04:00 UTC: Incremental backup (WAL copy)."""
    logger.info("Scheduled job: incremental_backup")
    result = backup_database_incremental()
    logger.info(f"incremental_backup result: {result}")


async def job_full_backup():
    """Weekly Sunday 05:00 UTC: Full database backup."""
    logger.info("Scheduled job: full_backup")
    result = backup_database_full()
    logger.info(f"full_backup result: {result}")


async def job_check_signal_outcomes():
    """Daily 06:00 UTC: Evaluate unaudited signal outcomes via SignalOutcomeTracker."""
    logger.info("Scheduled job: check_signal_outcomes")
    tracker = SignalOutcomeTracker()
    async with get_db() as db:
        results = await tracker.check_outcomes(db)
    logger.info(f"check_signal_outcomes result: evaluated {len(results)} signals")


async def job_update_bayesian_weights():
    """Daily 07:00 UTC: Update Bayesian dimension weights from last 90 days of outcomes."""
    logger.info("Scheduled job: update_bayesian_weights")
    try:
        from backend.quant.scoring import _get_adapter
        from backend.quant.signal_outcomes import SignalOutcomeTracker

        adapter = _get_adapter()
        tracker = SignalOutcomeTracker()

        async with get_db() as db:
            # Fetch evaluated signal outcomes from the last 90 days.
            # mock-filtered: only learn from real-data signals (IMPL-BAYESIAN-001 #2).
            cursor = await db.execute("""
                SELECT gex_score, vix_score, crypto_score, darkpool_score,
                       forward_return, trigger_time, alert_level
                FROM signal_alerts
                WHERE outcome IS NOT NULL
                  AND (mock_count = 0 OR mock_count IS NULL)
                  AND outcome_checked_at >= datetime('now', '-90 days')
                ORDER BY outcome_checked_at ASC
            """)
            rows = await cursor.fetchall()

        if not rows:
            logger.info("update_bayesian_weights: no evaluated outcomes in last 90 days")
            return

        outcomes = [dict(r) for r in rows]
        new_weights = adapter.update_weights(outcomes)
        logger.info(
            f"update_bayesian_weights: updated from {len(outcomes)} outcomes "
            f"→ {new_weights}"
        )

        # Persist adapted posterior state so weights survive restarts
        # (IMPL-BAYESIAN-001 #1).
        try:
            from backend.quant.scoring import persist_posteriors
            await persist_posteriors()
        except Exception as persist_exc:
            logger.warning(f"update_bayesian_weights persist failed: {persist_exc}")

    except Exception as exc:
        logger.error(f"update_bayesian_weights failed: {exc}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_jobs() -> None:
    """Register all scheduled maintenance jobs.

    Schedule:
        - Every hour:         verify_write_paths
        - Daily 02:00 UTC:    VACUUM + ANALYZE
        - Daily 03:00 UTC:    Data archiving (gex_strikes > 180 days)
        - Daily 04:00 UTC:    Incremental backup
        - Sunday 05:00 UTC:   Full backup
    """
    # Hourly: verify write paths
    scheduler.add_job(
        job_verify_write_paths,
        trigger=IntervalTrigger(hours=1),
        id="verify_write_paths",
        name="Verify write paths",
        replace_existing=True,
    )

    # Daily 02:00 UTC: VACUUM + ANALYZE
    scheduler.add_job(
        job_vacuum_analyze,
        trigger=CronTrigger(hour=2, minute=0),
        id="vacuum_analyze",
        name="VACUUM + ANALYZE",
        replace_existing=True,
    )

    # Daily 03:00 UTC: Data archiving
    scheduler.add_job(
        job_archive_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="archive_old_data",
        name="Archive old gex_strikes data",
        replace_existing=True,
    )

    # Daily 04:00 UTC: Incremental backup
    scheduler.add_job(
        job_incremental_backup,
        trigger=CronTrigger(hour=4, minute=0),
        id="incremental_backup",
        name="Incremental database backup",
        replace_existing=True,
    )

    # Weekly Sunday 05:00 UTC: Full backup
    scheduler.add_job(
        job_full_backup,
        trigger=CronTrigger(day_of_week="sun", hour=5, minute=0),
        id="full_backup",
        name="Full database backup",
        replace_existing=True,
    )

    # Daily 06:00 UTC: Signal outcome evaluation
    scheduler.add_job(
        job_check_signal_outcomes,
        trigger=CronTrigger(hour=6, minute=0),
        id="check_signal_outcomes",
        name="Evaluate signal outcomes (false positive tracking)",
        replace_existing=True,
    )

    # Daily 07:00 UTC: Bayesian weight update
    scheduler.add_job(
        job_update_bayesian_weights,
        trigger=CronTrigger(hour=7, minute=0),
        id="update_bayesian_weights",
        name="Update Bayesian dimension weights (90-day window)",
        replace_existing=True,
    )

    logger.info(
        "Scheduled 7 maintenance jobs: "
        "hourly write-path check, daily vacuum/archive/backup/outcomes/weights, weekly full backup"
    )


def start_scheduler() -> None:
    """Start the APScheduler. Call during FastAPI lifespan startup."""
    register_jobs()
    scheduler.start()
    logger.info("APScheduler started")


def stop_scheduler() -> None:
    """Shutdown the APScheduler. Call during FastAPI lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
