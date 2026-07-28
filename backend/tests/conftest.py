"""
Pytest configuration and shared fixtures for the Multi-source Resonance test suite.

Provides:
- In-memory SQLite database for test isolation
- Test-specific Settings (mock mode, no external API keys)
- FastAPI TestClient fixture
- Async test support via pytest-asyncio
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio

# Force test environment before any backend imports
os.environ["JWT_SECRET"] = "test-secret-key-not-for-production"
os.environ["DB_PATH"] = ":memory:"

from backend.config import Settings
from backend.database import SCHEMA_TABLES, SCHEMA_VIEWS, SEED_CONFIG


# ---------------------------------------------------------------------------
# Event loop fixture (session-scoped for pytest-asyncio)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Settings fixture — mock mode, no real API keys
# ---------------------------------------------------------------------------

@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return a Settings instance configured for testing (all mock mode)."""
    db_path = str(tmp_path / "test_resonance.db")
    return Settings(
        db_path=db_path,
        gexmetrix_api_key=None,
        axlfi_api_key=None,
        crypto_api_key=None,
        darkpool_api_key=None,
        jwt_secret="test-secret-key-not-for-production",
        jwt_algorithm="HS256",
        jwt_expire_minutes=30,
        log_level="DEBUG",
        fetch_interval_seconds=60,
        fetch_timeout_seconds=10,
        max_workers=4,
    )


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_db(tmp_path: Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Create an in-memory SQLite database with full schema for testing."""
    db_path = tmp_path / "test_resonance.db"
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row

    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(SCHEMA_TABLES)
    await conn.executescript(SCHEMA_VIEWS)
    await conn.executescript(SEED_CONFIG)
    await conn.commit()

    yield conn

    await conn.close()


@pytest_asyncio.fixture
async def populated_db(test_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Database pre-populated with sample data for query tests."""
    now = datetime.now(timezone.utc).isoformat()

    # Insert sample GEX snapshot
    await test_db.execute(
        """INSERT INTO gex_snapshots
           (symbol, timestamp, filename, net_gex, call_gex, put_gex,
            zero_gamma_level, call_wall, put_wall, spot_price,
            total_gamma, quality_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("SPX", now, "test.json", 1e9, 2e9, -1e9,
         5700.0, 5800.0, 5600.0, 5750.0,
         3e9, 0.95),
    )

    # Insert sample VIX data
    await test_db.execute(
        """INSERT INTO vix_analysis
           (timestamp, vix_spot, vx1, vx2, term_structure_ratio,
            term_structure_state, panic_premium)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (now, 15.5, 16.0, 17.0, 0.0625, "contango", -0.5),
    )

    # Insert sample signal alert
    await test_db.execute(
        """INSERT INTO signal_alerts
           (trigger_time, total_score, gex_score, vix_score,
            crypto_score, darkpool_score, alert_level)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (now, 3.5, 2.0, 1.0, 0.5, 0.0, "LEVEL_2"),
    )

    await test_db.commit()
    return test_db


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncGenerator:
    """Create a FastAPI TestClient with test database."""
    from httpx import ASGITransport, AsyncClient

    db_path = str(tmp_path / "test_app.db")

    # Patch settings before app import
    with patch("backend.config.settings") as mock_settings:
        mock_settings.db_path = db_path
        mock_settings.db_absolute_path = Path(db_path).resolve()
        mock_settings.jwt_secret = "test-secret-key-not-for-production"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expire_minutes = 30
        mock_settings.log_level = "DEBUG"
        mock_settings.fetch_interval_seconds = 60
        mock_settings.fetch_timeout_seconds = 10
        mock_settings.max_workers = 4
        mock_settings.cors_origins = "http://localhost:5173"
        mock_settings.cors_origin_list = ["http://localhost:5173"]
        mock_settings.is_mock_mode.return_value = True
        mock_settings.host = "127.0.0.1"
        mock_settings.port = 8524

        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ---------------------------------------------------------------------------
# Auth helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers():
    """Generate valid JWT auth headers for test requests."""
    from backend.api.middleware.auth import create_access_token

    token = create_access_token({"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token():
    """Create an access token for the default admin user."""
    from backend.api.middleware.auth import create_access_token

    return create_access_token({"sub": "admin"})


# ---------------------------------------------------------------------------
# Mock fetcher helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gex_data():
    """Sample GEX mock data matching GEXMetrixFetcher._mock_data() output."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "snapshots": [{
            "symbol": "SPX",
            "timestamp": now,
            "filename": "mock_spx_test.json",
            "net_gex": 500_000_000.0,
            "call_gex": 1_200_000_000.0,
            "put_gex": -700_000_000.0,
            "zero_gamma_level": 5700.0,
            "call_wall": 5800.0,
            "put_wall": 5600.0,
            "spot_price": 5750.0,
            "total_gamma": 1_900_000_000.0,
            "file_size": 10_000_000,
            "quality_score": 0.95,
            "data_lag_seconds": 60,
            "oi_coverage_pct": 98.0,
        }],
        "strikes": [],
        "fetch_timestamp": now,
        "symbol_count": 1,
        "total_strikes": 0,
    }


@pytest.fixture
def mock_vix_data():
    """Sample VIX mock data."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vix_spot": 15.5,
        "vx1": 16.0,
        "vx2": 17.0,
        "term_structure_ratio": 0.0625,
        "term_structure_state": "contango",
        "panic_premium": -0.5,
    }


@pytest.fixture
def mock_crypto_data():
    """Sample crypto derivatives mock data."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "btc_funding_rate": 0.0001,
        "btc_oi": 22000.0,
        "oi_change_1h": 0.02,
        "liquidation_spike": False,
        "cryptoquant_elr": 1.8,
        "funding_anomaly": False,
        "oi_crash": False,
        "leverage_cleanup": False,
    }


@pytest.fixture
def mock_darkpool_data():
    """Sample dark pool mock data."""
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "dix_value": 52.0,
        "chartexchange_short_ratio": 3.2,
        "stockgrid_20d_slope": 0.15,
        "stockgrid_60d_slope": -0.05,
        "stockgrid_divergence": False,
        "dbmf_ma5_recovery": True,
        "dix_signal": True,
        "short_ratio_signal": False,
        "stockgrid_signal": False,
        "aggregated_signal": True,
        "v_net": 150.0,
        "ema_fast_5": 100.0,
        "ema_slow_20": -50.0,
        "zero_cross_signal": "bullish_cross",
        "momentum_reversal_signal": "reversal_up",
    }
