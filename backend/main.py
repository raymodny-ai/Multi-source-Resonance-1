"""
FastAPI application entry point for the Multi-source Resonance Monitoring System.

Run with:
    python -m backend.main          # direct execution
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8524
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.middleware.auth import jwt_write_middleware
from backend.api.middleware.rate_limit import init_rate_limiter
from backend.api.routes.auth import init_auth, router as auth_router
from backend.api.routes.dashboard import router as dashboard_router
from backend.api.routes.gex import router as gex_router
from backend.api.routes.vix import router as vix_router
from backend.api.routes.crypto import router as crypto_router
from backend.api.routes.darkpool import router as darkpool_router
from backend.api.routes.signals import router as signals_router
from backend.api.routes.system import router as system_router
from backend.api.routes.config import router as config_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.analysis import router as analysis_router
from backend.api.routes.options_greeks import router as options_greeks_router
from backend.api.websocket import router as ws_router, setup_event_bus_bridge
from backend.config import settings
from backend.database import close_db, init_db
from backend.eventbus import EventBus
from backend.fetchers import (
    GEXMetrixFetcher, AXLFIFetcher, CBOEFetcher, VIXFetcher, YFinanceFetcher,
    CryptoFetcher, DarkpoolFetcher, FlowFetcher, LLMFetcher, MacroFetcher,
    PutCallFetcher, SectorFetcher, SentimentFetcher, VIXTermFetcher,
    SqueezeMetricsFetcher, FinraFetcher, CCDataFetcher, StockGridFetcher,
    CoinglassFetcher, TradierFetcher, DBMFFetcher, OptionsChainGreeksFetcher,
)
from backend.models.common import ErrorResponse, HealthCheck
from backend.pipeline import Pipeline
from backend.utils.scheduler import start_scheduler, stop_scheduler

# ── Logging setup ─────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# ── Application lifespan ──────────────────────────────────────────────────────

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    global _start_time
    _start_time = time.time()

    logger.info("Starting Multi-source Resonance v3.1", db_path=settings.db_path)
    await init_db()
    logger.info("Database initialized")

    # Initialize auth subsystem (create blacklist table, load from DB)
    await init_auth()
    logger.info("Auth subsystem initialized")

    # Initialize EventBus (async pub/sub for three-layer decoupling)
    event_bus = EventBus()
    app.state.event_bus = event_bus
    logger.info("EventBus initialized")

    # Initialize Pipeline V2.0 (collect → analyse → score)
    # Instantiate all 21 fetchers with shared config
    fetchers = [
        GEXMetrixFetcher(settings), AXLFIFetcher(settings), CBOEFetcher(settings),
        VIXFetcher(settings), YFinanceFetcher(settings),
        CryptoFetcher(settings), DarkpoolFetcher(settings), FlowFetcher(settings),
        LLMFetcher(settings), MacroFetcher(settings), PutCallFetcher(settings),
        SectorFetcher(settings), SentimentFetcher(settings), VIXTermFetcher(settings),
        SqueezeMetricsFetcher(settings), FinraFetcher(settings), CCDataFetcher(settings),
        StockGridFetcher(settings), CoinglassFetcher(settings), TradierFetcher(settings),
        DBMFFetcher(settings), OptionsChainGreeksFetcher(settings),
    ]
    pipeline = Pipeline(config=settings, event_bus=event_bus, fetchers=fetchers)
    app.state.pipeline = pipeline
    logger.info("Pipeline V2.0 initialized")

    # Start scheduled maintenance jobs
    start_scheduler()

    # Start periodic data collection pipeline (background, fetch_interval_seconds)
    # 21 fetcher default 60s 太频繁 — yfinance 会限速, 改 900s (15min) 合适
    if not pipeline.is_running:
        pipeline.start_background()
        logger.info("Periodic pipeline started (background task)")

    # Setup WebSocket <-> EventBus bridge
    await setup_event_bus_bridge(event_bus)
    logger.info("WebSocket <-> EventBus bridge established")

    yield

    # Shutdown pipeline
    await pipeline.stop()
    logger.info("Pipeline stopped")

    # Shutdown scheduler
    stop_scheduler()
    await close_db()
    logger.info("Application shutdown complete")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-source Resonance Monitoring System",
    description=(
        "Real-time cross-asset resonance detection: GEX, VIX term structure, "
        "crypto leverage cleanup, and darkpool DIX convergence."
    ),
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS middleware ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handlers ─────────────────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured error for request validation failures."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            message="Validation error",
            detail=str(exc.errors()),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — prevents raw tracebacks leaking."""
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            detail=str(exc) if settings.log_level == "DEBUG" else None,
        ).model_dump(),
    )


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthCheck, tags=["system"])
async def health_check():
    """Liveness probe — returns 200 when the service is running."""
    uptime = time.time() - _start_time if _start_time else 0.0
    return HealthCheck(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        version="3.1.0",
        uptime_seconds=round(uptime, 2),
    )


# ── Rate limiter ──────────────────────────────────────────────────────────────

init_rate_limiter(app)

# ── JWT write-protection middleware ────────────────────────────────────────────
# Must be added AFTER CORS so that OPTIONS preflight requests pass through.

app.middleware("http")(jwt_write_middleware)

# ── Route registration ────────────────────────────────────────────────────────

# Auth routes (login / refresh / logout)
app.include_router(auth_router)

# Dashboard BFF aggregation routes
app.include_router(dashboard_router)

# GEX data routes
app.include_router(gex_router)

# VIX data routes
app.include_router(vix_router)

# Crypto derivatives routes
app.include_router(crypto_router)

# Dark pool routes
app.include_router(darkpool_router)

# Signal & alerts routes
app.include_router(signals_router)

# System control routes (status, logs, source-status, auto-polling, collect-manual)
app.include_router(system_router)

# Configuration management routes
app.include_router(config_router)

# Metrics routes (Prometheus + JSON summary)
app.include_router(metrics_router)

# Analysis results routes
app.include_router(analysis_router)

# Options chain + Greeks (yfinance + py_vollib Black-Scholes local calc)
app.include_router(options_greeks_router)

# WebSocket route
app.include_router(ws_router)

# ── System control endpoints (pipeline start/stop) ────────────────────────────


@app.get("/api/system/start-collect", tags=["system"])
async def start_collection(request: Request):
    """Start the periodic data collection pipeline (reserved endpoint)."""
    pipeline: Pipeline = request.app.state.pipeline
    if pipeline.is_running:
        return {"ok": False, "message": "Pipeline already running"}
    pipeline.start_background()
    return {"ok": True, "message": "Pipeline started"}


@app.get("/api/system/stop-collect", tags=["system"])
async def stop_collection(request: Request):
    """Stop the periodic data collection pipeline (reserved endpoint)."""
    pipeline: Pipeline = request.app.state.pipeline
    if not pipeline.is_running:
        return {"ok": False, "message": "Pipeline not running"}
    await pipeline.stop()
    return {"ok": True, "message": "Pipeline stopped"}


@app.get("/api/system/pipeline-status", tags=["system"])
async def pipeline_status(request: Request):
    """Return current pipeline status and EventBus diagnostics."""
    pipeline: Pipeline = request.app.state.pipeline
    event_bus: EventBus = request.app.state.event_bus
    return {
        "pipeline": pipeline.get_status(),
        "event_bus": event_bus.get_stats(),
    }


# ── Tickers endpoint ──────────────────────────────────────────────────────────


@app.get("/api/tickers", tags=["system"])
async def get_tickers():
    """List of monitorable underlying symbols."""
    return {
        "tickers": [
            {"symbol": "SPX", "name": "S&P 500 Index", "priority": "core"},
            {"symbol": "SPY", "name": "S&P 500 ETF", "priority": "core"},
            {"symbol": "QQQ", "name": "Nasdaq-100 ETF", "priority": "core"},
            {"symbol": "IWM", "name": "Russell 2000 ETF", "priority": "core"},
            {"symbol": "NDX", "name": "Nasdaq-100 Index", "priority": "core"},
            {"symbol": "VIX", "name": "Volatility Index", "priority": "core"},
        ]
    }

# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
