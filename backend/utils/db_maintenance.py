"""
Database maintenance utilities: VACUUM, data archiving, write-path verification, backup.
"""

import logging
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from backend.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# VACUUM + ANALYZE
# ─────────────────────────────────────────────────────────────────────────────

async def vacuum_and_analyze() -> dict:
    """Execute SQLite VACUUM + ANALYZE to reclaim space and update query planner stats.

    FIX-25: VACUUM acquires an exclusive lock and conflicts with the
    long-running pipeline. We do a WAL checkpoint first (non-exclusive),
    then retry VACUUM with backoff — if it still can't acquire the lock
    we just log and return ``status=deferred`` so the cron job doesn't
    surface a confusing error.

    Returns a summary dict with status and timing.
    """
    import asyncio
    db_path = settings.db_absolute_path
    start = datetime.now(timezone.utc)

    try:
        # Always do a WAL checkpoint first — non-exclusive.
        try:
            chk = await aiosqlite.connect(str(db_path))
            try:
                await chk.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                await chk.commit()
            finally:
                await chk.close()
        except Exception as e:
            logger.warning(f"WAL checkpoint before VACUUM failed: {e}")

        # VACUUM requires exclusive access — retry with backoff.
        vacuum_done = False
        last_err: str | None = None
        for attempt in range(3):
            conn = await aiosqlite.connect(str(db_path))
            try:
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("VACUUM")
                await conn.execute("ANALYZE")
                await conn.commit()
                vacuum_done = True
                break
            except Exception as e:
                last_err = str(e)
                logger.warning(
                    f"VACUUM attempt {attempt + 1} failed: {e}; backing off"
                )
                await asyncio.sleep(10 * (attempt + 1))
            finally:
                await conn.close()

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        if not vacuum_done:
            logger.warning(
                f"VACUUM deferred after 3 attempts (last error: {last_err}); "
                f"DB is still usable, just won't reclaim space this cycle"
            )
            return {
                "status": "deferred",
                "operation": "vacuum_analyze",
                "error": last_err,
                "elapsed_seconds": round(elapsed, 2),
            }

        logger.info(f"VACUUM + ANALYZE completed in {elapsed:.2f}s")
        return {
            "status": "ok",
            "operation": "vacuum_analyze",
            "elapsed_seconds": round(elapsed, 2),
        }

    except Exception as e:
        logger.error(f"VACUUM + ANALYZE failed: {e}")
        return {"status": "error", "operation": "vacuum_analyze", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Data archiving — gex_strikes aging
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_archive_table(conn: aiosqlite.Connection) -> None:
    """Create gex_strikes_archive table if it doesn't exist (same schema as gex_strikes)."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS gex_strikes_archive (
            id          INTEGER PRIMARY KEY,
            snapshot_id INTEGER NOT NULL,
            symbol      TEXT NOT NULL,
            timestamp   DATETIME NOT NULL,
            strike      REAL NOT NULL,
            call_gex    REAL NOT NULL DEFAULT 0,
            put_gex     REAL NOT NULL DEFAULT 0,
            call_oi     INTEGER NOT NULL DEFAULT 0,
            put_oi      INTEGER NOT NULL DEFAULT 0,
            call_vol    INTEGER NOT NULL DEFAULT 0,
            put_vol     INTEGER NOT NULL DEFAULT 0,
            net_gex     REAL NOT NULL DEFAULT 0,
            archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_gex_strikes_archive_ts
        ON gex_strikes_archive (symbol, timestamp DESC)
    """)


async def archive_old_data(days: int = 180) -> dict:
    """Move gex_strikes data older than N days to the archive table.

    Args:
        days: Age threshold in days. Data older than this is archived.

    Returns:
        Summary dict with archived row count and status.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    db_path = settings.db_absolute_path

    try:
        conn = await aiosqlite.connect(str(db_path))
        conn.row_factory = aiosqlite.Row
        try:
            await conn.execute("PRAGMA journal_mode=WAL")
            await _ensure_archive_table(conn)

            # Count rows to archive
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM gex_strikes WHERE timestamp < ?",
                (cutoff_str,),
            )
            row = await cursor.fetchone()
            count = row[0] if row else 0

            if count == 0:
                logger.info(f"No gex_strikes data older than {days} days to archive")
                return {"status": "ok", "archived_rows": 0, "cutoff": cutoff_str}

            # Copy old data to archive
            await conn.execute("""
                INSERT OR IGNORE INTO gex_strikes_archive
                (id, snapshot_id, symbol, timestamp, strike, call_gex, put_gex,
                 call_oi, put_oi, call_vol, put_vol, net_gex)
                SELECT id, snapshot_id, symbol, timestamp, strike, call_gex, put_gex,
                       call_oi, put_oi, call_vol, put_vol, net_gex
                FROM gex_strikes
                WHERE timestamp < ?
            """, (cutoff_str,))

            # Delete archived data from main table
            await conn.execute(
                "DELETE FROM gex_strikes WHERE timestamp < ?",
                (cutoff_str,),
            )

            await conn.commit()
            logger.info(f"Archived {count} gex_strikes rows older than {days} days")
            return {"status": "ok", "archived_rows": count, "cutoff": cutoff_str}

        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Data archiving failed: {e}")
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Write-path verification
# ─────────────────────────────────────────────────────────────────────────────

async def verify_write_paths() -> dict:
    """Check whether validation_audit_log and gateway_snapshots tables have active writers.

    If these tables have 0 rows, it means the validation pipeline / gateway snapshot
    recording code paths have not been activated yet. Log warnings accordingly.

    Returns:
        Dict with write-path status for each monitored table.
    """
    results = {}
    tables_to_check = ["validation_audit_log", "gateway_snapshots"]

    try:
        async with _get_read_conn() as conn:
            for table in tables_to_check:
                try:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                    row = await cursor.fetchone()
                    count = row[0] if row else 0
                    results[table] = {"row_count": count, "active": count > 0}

                    if count == 0:
                        logger.warning(
                            f"Table '{table}' has 0 rows — write path may not be activated. "
                            f"Check that the validation pipeline / gateway snapshot recorder is running."
                        )
                    else:
                        logger.debug(f"Table '{table}' has {count} rows — write path active")
                except Exception as e:
                    results[table] = {"row_count": -1, "active": False, "error": str(e)}
                    logger.error(f"Failed to check table '{table}': {e}")

    except Exception as e:
        logger.error(f"Write-path verification failed: {e}")
        return {"status": "error", "error": str(e)}

    return {"status": "ok", "tables": results}


class _ReadConnContext:
    """Async context manager for read-only DB access."""
    async def __aenter__(self):
        db_path = settings.db_absolute_path
        self.conn = await aiosqlite.connect(str(db_path))
        self.conn.row_factory = aiosqlite.Row
        return self.conn
    async def __aexit__(self, *args):
        await self.conn.close()


def _get_read_conn():
    """Return an async context manager for read-only DB access."""
    return _ReadConnContext()


# ─────────────────────────────────────────────────────────────────────────────
# Database backup
# ─────────────────────────────────────────────────────────────────────────────

def _get_backup_dir() -> Path:
    """Get or create the backup directory."""
    backup_dir = settings.db_absolute_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_database_full() -> dict:
    """Perform a full database backup using SQLite's .backup() command.

    Used for weekly full backups. Backup file is named:
    resonance_full_YYYYMMDD_HHMMSS.db

    Returns:
        Summary dict with backup path and size.
    """
    db_path = settings.db_absolute_path
    backup_dir = _get_backup_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"resonance_full_{timestamp}.db"

    try:
        # Use synchronous sqlite3 for backup (reliable .backup() API)
        src = sqlite3.connect(str(db_path))
        try:
            dst = sqlite3.connect(str(backup_path))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info(f"Full backup created: {backup_path.name} ({size_mb:.1f} MB)")

        # Clean old backups (retain 30 days)
        _cleanup_old_backups(backup_dir, keep_days=30)

        return {
            "status": "ok",
            "type": "full",
            "path": str(backup_path),
            "size_mb": round(size_mb, 2),
        }

    except Exception as e:
        logger.error(f"Full backup failed: {e}")
        return {"status": "error", "type": "full", "error": str(e)}


def backup_database_incremental() -> dict:
    """Perform an incremental backup by copying the WAL file.

    Used for daily incremental backups. The WAL file contains all changes
    since the last checkpoint.

    Returns:
        Summary dict with backup status.
    """
    db_path = settings.db_absolute_path
    wal_path = Path(str(db_path) + "-wal")
    backup_dir = _get_backup_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    try:
        if not wal_path.exists():
            logger.info("No WAL file found — performing full backup instead")
            return backup_database_full()

        # Copy WAL file
        wal_backup = backup_dir / f"resonance_wal_{timestamp}.db-wal"
        shutil.copy2(str(wal_path), str(wal_backup))

        # Also copy the main DB file (needed to restore with WAL)
        db_backup = backup_dir / f"resonance_incr_{timestamp}.db"
        shutil.copy2(str(db_path), str(db_backup))

        size_mb = (wal_backup.stat().st_size + db_backup.stat().st_size) / (1024 * 1024)
        logger.info(f"Incremental backup created: {db_backup.name} + WAL ({size_mb:.1f} MB)")

        # Clean old backups
        _cleanup_old_backups(backup_dir, keep_days=30)

        return {
            "status": "ok",
            "type": "incremental",
            "path": str(db_backup),
            "wal_path": str(wal_backup),
            "size_mb": round(size_mb, 2),
        }

    except Exception as e:
        logger.error(f"Incremental backup failed: {e}")
        return {"status": "error", "type": "incremental", "error": str(e)}


def _cleanup_old_backups(backup_dir: Path, keep_days: int = 30) -> None:
    """Remove backup files older than keep_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    removed = 0

    for f in backup_dir.iterdir():
        if f.is_file() and f.suffix in (".db", ".db-wal"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                try:
                    f.unlink()
                    removed += 1
                except OSError as e:
                    logger.warning(f"Failed to remove old backup {f.name}: {e}")

    if removed:
        logger.info(f"Cleaned up {removed} old backup(s) (retention: {keep_days} days)")
