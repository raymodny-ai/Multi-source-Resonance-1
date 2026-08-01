"""
Integration tests for the FastAPI application endpoints.

Tests:
- Health check GET /api/health
- Authentication flow (login -> access -> refresh -> logout)
- Main GET endpoints return correct format
- Write operations require JWT (401 without token)
- Rate limiting (fast requests trigger 429)
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app_client(tmp_path: Path):
    """Create a test client with a fresh database."""
    db_path = str(tmp_path / "api_test.db")

    with patch("backend.config.settings") as mock_settings, \
         patch("backend.database.settings", mock_settings):
        mock_settings.db_path = db_path
        mock_settings.db_absolute_path = Path(db_path).resolve()
        mock_settings.jwt_secret = "test-secret-key-not-for-production"
        # FIX-05: auth routes call ``settings.effective_jwt_secret`` (which
        # would emit a warning + ephemeral fallback in production). The
        # test fixture wires in the explicit value to keep behaviour
        # deterministic and avoid the per-process random fallback masking
        # bugs in token creation.
        mock_settings.effective_jwt_secret = "test-secret-key-not-for-production"
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
        from backend.eventbus.event_bus import EventBus

        # Create the database file so get_db() works
        import aiosqlite
        from backend.database import SCHEMA_TABLES, SCHEMA_VIEWS, SEED_CONFIG
        conn = await aiosqlite.connect(db_path)
        await conn.executescript(SCHEMA_TABLES)
        await conn.executescript(SCHEMA_VIEWS)
        await conn.executescript(SEED_CONFIG)
        await conn.commit()
        await conn.close()

        # Mock pipeline in app.state so endpoints that access it don't crash
        class _MockPipeline:
            is_running = False
            cycle_count = 0
            fetchers = []
            config = mock_settings
            def get_status(self):
                return {"running": False, "cycle_count": 0, "fetcher_count": 0, "analyzer_count": 0, "has_scorer": False}

        app.state.pipeline = _MockPipeline()
        app.state.event_bus = EventBus()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def auth_client(app_client: AsyncClient):
    """Client with valid JWT in headers."""
    from backend.api.middleware.auth import create_access_token

    token = create_access_token({"sub": "admin"})
    app_client.headers["Authorization"] = f"Bearer {token}"
    return app_client


# ===========================================================================
# Health check
# ===========================================================================

class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, app_client: AsyncClient):
        resp = await app_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_has_uptime(self, app_client: AsyncClient):
        resp = await app_client.get("/api/health")
        data = resp.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))


# ===========================================================================
# Authentication flow
# ===========================================================================

class TestAuthFlow:

    @pytest.mark.asyncio
    async def test_login_success(self, app_client: AsyncClient):
        resp = await app_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, app_client: AsyncClient):
        resp = await app_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, app_client: AsyncClient):
        resp = await app_client.post("/api/auth/login", json={
            "username": "admin",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self, app_client: AsyncClient):
        # Login first
        login_resp = await app_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin",
        })
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = await app_client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self, app_client: AsyncClient):
        resp = await app_client.post("/api/auth/logout", json={})
        # Should return 401 without Bearer token
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, app_client: AsyncClient):
        # Login
        login_resp = await app_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin",
        })
        access_token = login_resp.json()["access_token"]

        # Logout with token
        app_client.headers["Authorization"] = f"Bearer {access_token}"
        logout_resp = await app_client.post("/api/auth/logout", json={
            "token": access_token,
        })
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Successfully logged out"


# ===========================================================================
# GET endpoints return correct format
# ===========================================================================

class TestGETEndpoints:

    @pytest.mark.asyncio
    async def test_tickers_endpoint(self, app_client: AsyncClient):
        resp = await app_client.get("/api/tickers")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert len(data["tickers"]) > 0
        assert "symbol" in data["tickers"][0]

    @pytest.mark.asyncio
    async def test_docs_accessible(self, app_client: AsyncClient):
        resp = await app_client.get("/api/docs")
        # Should return 200 (Swagger UI)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json(self, app_client: AsyncClient):
        resp = await app_client.get("/api/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data


# ===========================================================================
# Write operations require JWT
# ===========================================================================

class TestWriteProtection:

    @pytest.mark.asyncio
    async def test_post_without_token_returns_401(self, app_client: AsyncClient):
        """Write operations (POST) to non-public paths require JWT."""
        resp = await app_client.post("/api/signals/acknowledge/1", json={
            "acknowledged": True,
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_put_without_token_returns_401(self, app_client: AsyncClient):
        resp = await app_client.put("/api/config/test", json={
            "value": "test",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_without_token_returns_401(self, app_client: AsyncClient):
        resp = await app_client.delete("/api/signals/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_does_not_require_token(self, app_client: AsyncClient):
        """GET requests should pass through without JWT."""
        resp = await app_client.get("/api/health")
        assert resp.status_code == 200


# ===========================================================================
# Rate limiting
# ===========================================================================

class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_rapid_requests_to_auth(self, app_client: AsyncClient):
        """Auth endpoints have strict rate limit (10/minute)."""
        responses = []
        for _ in range(15):
            resp = await app_client.post("/api/auth/login", json={
                "username": "admin",
                "password": "wrong",
            })
            responses.append(resp.status_code)

        # At least one should be 429 (rate limited)
        assert 429 in responses


# ===========================================================================
# System endpoints
# ===========================================================================

class TestSystemEndpoints:

    @pytest.mark.asyncio
    async def test_metrics_summary(self, app_client: AsyncClient):
        resp = await app_client.get("/api/metrics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline" in data
        assert "event_bus" in data
