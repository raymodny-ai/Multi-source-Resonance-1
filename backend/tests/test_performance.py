"""
Performance baseline tests.

Tests:
- Dashboard-view response time < 50ms (with mock data)
- Mock fetcher concurrent execution time
- Database query performance
"""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from backend.config import Settings
from backend.database import SCHEMA_TABLES, SCHEMA_VIEWS, SEED_CONFIG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "perf_test.db"),
        jwt_secret="test",
        fetch_interval_seconds=60,
        fetch_timeout_seconds=10,
        max_workers=8,
    )


async def _create_populated_db(db_path: str) -> aiosqlite.Connection:
    """Create a DB with sample data for query performance tests."""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(SCHEMA_TABLES)
    await conn.executescript(SCHEMA_VIEWS)
    await conn.executescript(SEED_CONFIG)

    now = datetime.now(timezone.utc)

    # Insert 100 GEX snapshots
    for i in range(100):
        ts = now.isoformat()
        await conn.execute(
            """INSERT INTO gex_snapshots
               (symbol, timestamp, filename, net_gex, call_gex, put_gex,
                zero_gamma_level, call_wall, put_wall, spot_price,
                total_gamma, quality_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"SPX", ts, f"test_{i}.json", 1e9 * (i % 3 - 1),
             1.5e9, -0.5e9, 5700.0, 5800.0, 5600.0, 5750.0,
             2e9, 0.95),
        )

    # Insert 100 VIX records
    for i in range(100):
        await conn.execute(
            """INSERT INTO vix_analysis
               (timestamp, vix_spot, vx1, vx2, term_structure_ratio,
                term_structure_state, panic_premium)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (now.isoformat(), 15.0 + i * 0.1, 16.0, 17.0,
             0.0625, "contango", -1.0),
        )

    # Insert 50 signal alerts
    for i in range(50):
        await conn.execute(
            """INSERT INTO signal_alerts
               (trigger_time, total_score, gex_score, vix_score,
                crypto_score, darkpool_score, alert_level)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (now.isoformat(), 2.0 + i * 0.02, 1.0, 0.5, 0.3, 0.2,
             "LEVEL_1" if i < 25 else "LEVEL_2"),
        )

    await conn.commit()
    return conn


# ===========================================================================
# Dashboard-view response time
# ===========================================================================

class TestDashboardResponseTime:

    @pytest.mark.asyncio
    async def test_health_endpoint_latency(self, tmp_path: Path):
        """Health endpoint should respond in < 50ms."""
        from httpx import ASGITransport, AsyncClient

        db_path = str(tmp_path / "perf_health.db")

        with patch("backend.config.settings") as mock_settings:
            mock_settings.db_path = db_path
            mock_settings.db_absolute_path = Path(db_path).resolve()
            mock_settings.jwt_secret = "test"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_minutes = 30
            mock_settings.log_level = "WARNING"
            mock_settings.fetch_interval_seconds = 60
            mock_settings.fetch_timeout_seconds = 10
            mock_settings.max_workers = 4
            mock_settings.cors_origins = "*"
            mock_settings.cors_origin_list = ["*"]
            mock_settings.is_mock_mode.return_value = True
            mock_settings.host = "127.0.0.1"
            mock_settings.port = 8524

            from backend.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Warm up
                await client.get("/api/health")

                # Measure
                start = time.perf_counter()
                for _ in range(10):
                    resp = await client.get("/api/health")
                elapsed = time.perf_counter() - start

                avg_ms = (elapsed / 10) * 1000
                assert avg_ms < 50, f"Average health check took {avg_ms:.1f}ms (limit: 50ms)"
                assert resp.status_code == 200


# ===========================================================================
# Mock fetcher concurrent execution
# ===========================================================================

class TestFetcherConcurrency:

    @pytest.mark.asyncio
    async def test_mock_fetchers_concurrent_time(self, tmp_path: Path):
        """10 mock fetchers should complete concurrently in < 1 second."""
        from backend.eventbus.event_bus import EventBus
        from backend.pipeline.concurrent_executor import ConcurrentExecutor

        settings = _make_settings(tmp_path)
        bus = EventBus()
        executor = ConcurrentExecutor(settings, bus)

        class FastMockFetcher:
            def __init__(self, name):
                self._name = name

            @property
            def source_name(self):
                return self._name

            async def fetch_with_retry(self, **kwargs):
                await asyncio.sleep(0.01)  # 10ms simulated latency
                return {
                    "data": "mock",
                    "_meta": {
                        "source": self._name,
                        "is_mock": True,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "error": None,
                    },
                }

            async def close(self):
                pass

        fetchers = [FastMockFetcher(f"source_{i}") for i in range(10)]

        start = time.perf_counter()
        report = await executor.execute_fetchers(fetchers)
        elapsed = time.perf_counter() - start

        assert len(report.results) == 10
        # Concurrent execution should be much faster than 10 * 10ms = 100ms
        assert elapsed < 1.0, f"Concurrent fetch took {elapsed:.2f}s (limit: 1s)"
        executor.shutdown()


# ===========================================================================
# Database query performance
# ===========================================================================

class TestDatabaseQueryPerformance:

    @pytest.mark.asyncio
    async def test_gex_snapshot_query(self, tmp_path: Path):
        """Query 100 GEX snapshots should complete in < 50ms."""
        db_path = str(tmp_path / "perf_query.db")
        conn = await _create_populated_db(db_path)

        start = time.perf_counter()
        cursor = await conn.execute(
            "SELECT * FROM gex_snapshots ORDER BY timestamp DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000

        assert len(rows) == 100
        assert elapsed < 50, f"GEX snapshot query took {elapsed:.1f}ms (limit: 50ms)"
        await conn.close()

    @pytest.mark.asyncio
    async def test_vix_query(self, tmp_path: Path):
        """Query 100 VIX records should complete in < 50ms."""
        db_path = str(tmp_path / "perf_vix.db")
        conn = await _create_populated_db(db_path)

        start = time.perf_counter()
        cursor = await conn.execute(
            "SELECT * FROM vix_analysis ORDER BY timestamp DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000

        assert len(rows) == 100
        assert elapsed < 50, f"VIX query took {elapsed:.1f}ms (limit: 50ms)"
        await conn.close()

    @pytest.mark.asyncio
    async def test_signal_alerts_query(self, tmp_path: Path):
        """Query signal alerts with filter should complete in < 50ms."""
        db_path = str(tmp_path / "perf_signals.db")
        conn = await _create_populated_db(db_path)

        start = time.perf_counter()
        cursor = await conn.execute(
            "SELECT * FROM signal_alerts WHERE alert_level = ? ORDER BY trigger_time DESC",
            ("LEVEL_2",),
        )
        rows = await cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000

        assert len(rows) == 25
        assert elapsed < 50, f"Signal query took {elapsed:.1f}ms (limit: 50ms)"
        await conn.close()

    @pytest.mark.asyncio
    async def test_dashboard_view_query(self, tmp_path: Path):
        """Dashboard view query should complete in < 100ms."""
        db_path = str(tmp_path / "perf_dashboard.db")
        conn = await _create_populated_db(db_path)

        start = time.perf_counter()
        cursor = await conn.execute(
            "SELECT * FROM v_resonance_dashboard LIMIT 10"
        )
        rows = await cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"Dashboard view query took {elapsed:.1f}ms (limit: 100ms)"
        await conn.close()

    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, tmp_path: Path):
        """Batch insert 500 rows should complete in < 200ms."""
        db_path = str(tmp_path / "perf_insert.db")
        conn = await _create_populated_db(db_path)
        now = datetime.now(timezone.utc).isoformat()

        # Insert a snapshot first to satisfy FK constraint
        await conn.execute(
            """INSERT INTO gex_snapshots
               (symbol, timestamp, filename, net_gex)
               VALUES (?, ?, ?, ?)""",
            ("SPX", now, "perf.json", 1e9),
        )
        await conn.commit()
        cursor = await conn.execute("SELECT last_insert_rowid()")
        snap_row = await cursor.fetchone()
        snap_id = snap_row[0]

        rows = [
            (snap_id, "SPX", now, 5700.0 + i, 1e6, -1e6, 1000, 1000, 500, 500, 0)
            for i in range(500)
        ]

        start = time.perf_counter()
        await conn.executemany(
            """INSERT INTO gex_strikes
               (snapshot_id, symbol, timestamp, strike,
                call_gex, put_gex, call_oi, put_oi, call_vol, put_vol, net_gex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        await conn.commit()
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Batch insert took {elapsed:.1f}ms (limit: 200ms)"

        # Verify
        cursor = await conn.execute("SELECT COUNT(*) FROM gex_strikes")
        row = await cursor.fetchone()
        assert row[0] == 500
        await conn.close()
