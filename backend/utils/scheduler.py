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


# ─────────────────────────────────────────────────────────────────────────────
# Job wrappers (APScheduler calls these as async functions)
# ─────────────────────────────────────────────────────────────────────────────

async def job_verify_write_paths():
    """Hourly job: verify that validation_audit_log and gateway_snapshots have writers."""
    logger.info("Scheduled job: verify_write_paths")
    result = await verify_write_paths()
    logger.debug(f"verify_write_paths result: {result}")


async def job_vacuum_analyze():
    """Daily 02:00 UTC: VACUUM + ANALYZE the database."""
    logger.info("Scheduled job: vacuum_and_analyze")
    result = await vacuum_and_analyze()
    logger.info(f"vacuum_and_analyze result: {result}")


async def job_archive_old_data():
    """Daily 03:00 UTC: Archive gex_strikes data older than 180 days."""
    logger.info("Scheduled job: archive_old_data")
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

    logger.info(
        "Scheduled 6 maintenance jobs: "
        "hourly write-path check, daily vacuum/archive/backup/outcomes, weekly full backup"
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
