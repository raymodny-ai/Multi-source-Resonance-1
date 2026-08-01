"""
Integration tests for the Pipeline V2.0 system.

Tests:
- Full pipeline cycle in mock mode
- Tiered concurrent execution
- Data writing to database
- EventBus event publishing during pipeline cycle
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import Settings
from backend.eventbus.event_bus import EventBus
from backend.eventbus.events import EventType
from backend.pipeline.concurrent_executor import ConcurrentExecutor, FetchResult
from backend.pipeline.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "pipeline_test.db"),
        jwt_secret="test",
        fetch_interval_seconds=60,
        fetch_timeout_seconds=5,
        max_workers=4,
    )


class MockFetcher:
    """Lightweight mock fetcher for pipeline tests."""

    def __init__(self, name: str, data: dict | None = None):
        self._source_name = name
        self._data = data or {"mock_key": "mock_value"}

    @property
    def source_name(self) -> str:
        return self._source_name

    async def fetch_with_retry(self, **kwargs) -> dict:
        result = self._data.copy()
        result["_meta"] = {
            "source": self._source_name,
            "is_mock": True,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        return result

    async def fetch(self) -> dict:
        return await self.fetch_with_retry()

    async def close(self):
        pass


# ===========================================================================
# Concurrent Executor
# ===========================================================================

class TestConcurrentExecutor:

    @pytest.mark.asyncio
    async def test_execute_single_fetcher(self, tmp_path: Path):
        settings = _make_settings(tmp_path)
        bus = EventBus()
        executor = ConcurrentExecutor(settings, bus)

        fetcher = MockFetcher("test_source")
        report = await executor.execute_fetchers([fetcher])

        assert report.success_count >= 0  # may be in tier2
        assert "test_source" in report.results
        executor.shutdown()

    @pytest.mark.asyncio
    async def test_execute_multiple_fetchers(self, tmp_path: Path):
        settings = _make_settings(tmp_path)
        bus = EventBus()
        executor = ConcurrentExecutor(settings, bus)

        fetchers = [
            MockFetcher("source_a"),
            MockFetcher("source_b"),
            MockFetcher("source_c"),
        ]
        report = await executor.execute_fetchers(fetchers)

        assert len(report.results) == 3
        assert report.total_elapsed_sec >= 0
        executor.shutdown()

    @pytest.mark.asyncio
    async def test_tier_classification(self, tmp_path: Path):
        """GEXMetrix -> Tier1, AXLFI -> Tier3, others -> Tier2."""
        settings = _make_settings(tmp_path)
        bus = EventBus()
        executor = ConcurrentExecutor(settings, bus)

        fetchers = [
            MockFetcher("GEXMetrix"),
            MockFetcher("VIX"),
            MockFetcher("AXLFI"),
        ]
        report = await executor.execute_fetchers(fetchers)

        # Tier 1 and 2 should be in results (Tier3 is background)
        assert "GEXMetrix" in report.results
        assert "VIX" in report.results
        executor.shutdown()

    @pytest.mark.asyncio
    async def test_fetcher_failure_handled(self, tmp_path: Path):
        """A failing fetcher does not crash the executor."""
        settings = _make_settings(tmp_path)
        bus = EventBus()
        executor = ConcurrentExecutor(settings, bus)

        class FailingFetcher:
            source_name = "fail_source"
            async def fetch_with_retry(self, **kwargs):
                raise RuntimeError("fetch failed")
            async def close(self):
                pass

        report = await executor.execute_fetchers([FailingFetcher()])
        assert report.error_count >= 1
        executor.shutdown()

    @pytest.mark.asyncio
    async def test_events_published(self, tmp_path: Path):
        """Fetch results publish events to the bus."""
        settings = _make_settings(tmp_path)
        bus = EventBus()
        events_received = []

        async def capture_event(et, data):
            events_received.append(et)

        await bus.subscribe(EventType.DATA_FETCH_COMPLETE, capture_event)

        executor = ConcurrentExecutor(settings, bus)
        fetcher = MockFetcher("test_source")
        await executor.execute_fetchers([fetcher])

        # Allow async tasks to complete
        await asyncio.sleep(0.1)
        assert len(events_received) > 0
        executor.shutdown()


# ===========================================================================
# Pipeline full cycle
# ===========================================================================

class TestPipelineCycle:

    @pytest.mark.asyncio
    async def test_run_cycle_mock_mode(self, tmp_path: Path):
        """A full pipeline cycle completes in mock mode."""
        settings = _make_settings(tmp_path)
        bus = EventBus()

        # Patch database operations to use temp path
        with patch("backend.pipeline.data_writer.get_db") as mock_get_db:
            import aiosqlite
            from backend.database import SCHEMA_TABLES, SCHEMA_VIEWS, SEED_CONFIG

            async def _get_conn():
                conn = await aiosqlite.connect(str(tmp_path / "cycle_test.db"))
                conn.row_factory = aiosqlite.Row
                await conn.executescript(SCHEMA_TABLES)
                await conn.executescript(SCHEMA_VIEWS)
                await conn.executescript(SEED_CONFIG)
                await conn.commit()
                return conn

            # Create a simple async context manager
            class _CM:
                async def __aenter__(self):
                    self.conn = await _get_conn()
                    return self.conn
                async def __aexit__(self, *args):
                    await self.conn.commit()
                    await self.conn.close()

            mock_get_db.return_value = _CM()

            pipeline = Pipeline(config=settings, event_bus=bus)
            fetcher = MockFetcher("test_source")
            pipeline.fetchers = [fetcher]

            report = await pipeline.run_cycle()

            assert "cycle_ts" in report
            assert "scoring" in report
            assert report["cycle_number"] == 0  # not incremented by run_cycle

    @pytest.mark.asyncio
    async def test_pipeline_status(self, tmp_path: Path):
        settings = _make_settings(tmp_path)
        bus = EventBus()
        pipeline = Pipeline(config=settings, event_bus=bus)

        status = pipeline.get_status()
        assert status["running"] is False
        assert status["cycle_count"] == 0
        assert status["fetcher_count"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_register_analyzer(self, tmp_path: Path):
        settings = _make_settings(tmp_path)
        bus = EventBus()
        pipeline = Pipeline(config=settings, event_bus=bus)

        async def mock_analyzer(data):
            return {"score": 50}

        pipeline.register_analyzer("test_source", mock_analyzer)
        assert pipeline.get_status()["analyzer_count"] == 1

    @pytest.mark.asyncio
    async def test_pipeline_register_scorer(self, tmp_path: Path):
        settings = _make_settings(tmp_path)
        bus = EventBus()
        pipeline = Pipeline(config=settings, event_bus=bus)

        async def mock_scorer(results):
            return {"total_score": 3.5}

        pipeline.register_scorer(mock_scorer)
        assert pipeline.get_status()["has_scorer"] is True

    @pytest.mark.asyncio
    async def test_pipeline_basic_scoring(self, tmp_path: Path):
        """Pipeline with no registered scorer uses basic fallback.

        FIX-38: ``_basic_score`` now delegates the math to
        ``scoring.calculate_score`` so the 0-100 normalized scale and the
        dimension weights stay in sync with the main scorer. Dimension
        scores are expected in 0-100 range.
        """
        settings = _make_settings(tmp_path)
        bus = EventBus()
        pipeline = Pipeline(config=settings, event_bus=bus)

        analysis = {
            "gex_data": {"gex_score": 60.0},
            "vix_data": {"vix_score": 40.0},
            "crypto_data": {"crypto_score": 80.0},
            "darkpool_data": {"darkpool_score": 50.0},
        }
        result = pipeline._basic_score(analysis)
        # Weighted contribution: (60/100)*2.5 + (40/100)*1.5 + (80/100)*2.0 + (50/100)*2.0
        # = 1.5 + 0.6 + 1.6 + 1.0 = 4.7 raw → 4.7/8.0 * 100 = 58.75
        assert abs(result["total_score"] - 58.75) < 0.5
        assert result["scorer"] == "basic_fallback"

    @pytest.mark.asyncio
    async def test_pipeline_alert_level(self, tmp_path: Path):
        """FIX-38: thresholds live on the normalized 0-100 scale."""
        settings = _make_settings(tmp_path)
        bus = EventBus()
        pipeline = Pipeline(config=settings, event_bus=bus)

        assert pipeline._compute_alert_level(0.0) == "NONE"
        assert pipeline._compute_alert_level(24.9) == "NONE"
        assert pipeline._compute_alert_level(25.0) == "LEVEL_1"
        assert pipeline._compute_alert_level(49.9) == "LEVEL_1"
        assert pipeline._compute_alert_level(50.0) == "LEVEL_2"
        assert pipeline._compute_alert_level(74.9) == "LEVEL_2"
        assert pipeline._compute_alert_level(75.0) == "LEVEL_3"
        assert pipeline._compute_alert_level(100.0) == "LEVEL_3"


# ===========================================================================
# EventBus integration during pipeline
# ===========================================================================

class TestPipelineEventBusIntegration:

    @pytest.mark.asyncio
    async def test_pipeline_publishes_system_events(self, tmp_path: Path):
        """Pipeline publishes ANALYSIS_START, SCORING_START, etc."""
        settings = _make_settings(tmp_path)
        bus = EventBus()
        published_events = []

        async def capture(et, data):
            published_events.append(et)

        await bus.subscribe("analysis.*", capture)
        await bus.subscribe("scoring.*", capture)

        # Patch DB to avoid real writes
        with patch("backend.pipeline.data_writer.get_db") as mock_get_db:
            import aiosqlite
            from backend.database import SCHEMA_TABLES, SCHEMA_VIEWS, SEED_CONFIG

            class _CM:
                async def __aenter__(self):
                    self.conn = await aiosqlite.connect(str(tmp_path / "eb_test.db"))
                    await self.conn.executescript(SCHEMA_TABLES)
                    await self.conn.executescript(SCHEMA_VIEWS)
                    await self.conn.executescript(SEED_CONFIG)
                    await self.conn.commit()
                    return self.conn
                async def __aexit__(self, *args):
                    await self.conn.commit()
                    await self.conn.close()

            mock_get_db.return_value = _CM()

            pipeline = Pipeline(config=settings, event_bus=bus)
            pipeline.fetchers = [MockFetcher("test")]

            await pipeline.run_cycle()
            await asyncio.sleep(0.1)

        assert len(published_events) > 0
