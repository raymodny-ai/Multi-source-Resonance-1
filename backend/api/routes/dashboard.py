"""
Dashboard BFF (Backend-For-Frontend) aggregation routes.
Provides single-call endpoints that aggregate data from multiple dimensions.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from backend.database import get_db
from backend.quant import (
    gex_analyze,
    vix_analyze,
    crypto_analyze,
    darkpool_analyze,
    calculate_score,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


async def _live_compute_signal(
    gex_data, vix_data, crypto_data, darkpool_data,
) -> dict | None:
    """Live-compute a synthetic signal from the latest raw dimension rows.

    方案 A (2026-08-02): when there is no persisted signal_alerts row (e.g. the
    signal history was cleared, or the current market stays below the LEVEL_1
    trigger so no rows are ever written), the dashboard's four dimension score
    cards would render "— / 100". Instead of showing empty, run each dimension
    analyzer on the latest raw row and aggregate via calculate_score, returning
    a synthetic signal dict the frontend treats identically to a real one.

    Returns None when there is nothing to analyze (no raw data at all).
    """
    if not (gex_data or vix_data or crypto_data or darkpool_data):
        return None

    async def _score(analyzer, payload):
        if not payload or not isinstance(payload, dict):
            return 0.0
        try:
            res = await analyzer(payload)
            if isinstance(res, dict):
                return float(res.get("score") or 0.0)
        except Exception:
            logger.exception("live dimension analyze failed")
        return 0.0

    gex_s = await _score(gex_analyze, gex_data)
    vix_s = await _score(vix_analyze, vix_data)
    crypto_s = await _score(crypto_analyze, crypto_data)
    dark_s = await _score(darkpool_analyze, darkpool_data)

    scoring = calculate_score(
        gex_score=gex_s, vix_score=vix_s,
        crypto_score=crypto_s, darkpool_score=dark_s,
    )
    dims = scoring.get("dimension_scores", {})

    return {
        "total_score": float(scoring.get("normalized_score", 0.0)),
        "raw_score": float(scoring.get("raw_score", 0.0)),
        "gex_score": float(dims.get("gex", gex_s)),
        "vix_score": float(dims.get("vix", vix_s)),
        "crypto_score": float(dims.get("crypto", crypto_s)),
        "darkpool_score": float(dims.get("darkpool", dark_s)),
        "alert_level": str(scoring.get("level") or "LEVEL_0"),
        "signals": scoring.get("signals", []),
        # marker so the UI can distinguish live-computed vs persisted signal
        "live_computed": True,
        "trigger_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
async def dashboard_view():
    """BFF aggregation endpoint — returns latest data from all dimensions.

    Aggregates GEX, VIX, Crypto, Darkpool, and signal scores from the database
    without re-computing. Target response time < 10ms.
    """
    async with get_db() as db:
        # Fetch latest GEX snapshot (SPX as primary)
        gex_cursor = await db.execute("""
            SELECT * FROM v_latest_gex_snapshot
            WHERE symbol = 'SPX'
        """)
        gex_row = await gex_cursor.fetchone()
        gex_data = dict(gex_row) if gex_row else None

        # Fetch latest VIX data
        vix_cursor = await db.execute("""
            SELECT * FROM vix_analysis
            ORDER BY timestamp DESC LIMIT 1
        """)
        vix_row = await vix_cursor.fetchone()
        vix_data = dict(vix_row) if vix_row else None

        # Fetch latest crypto data
        crypto_cursor = await db.execute("""
            SELECT * FROM crypto_derivatives
            ORDER BY timestamp DESC LIMIT 1
        """)
        crypto_row = await crypto_cursor.fetchone()
        crypto_data = dict(crypto_row) if crypto_row else None

        # Fetch latest darkpool data
        darkpool_cursor = await db.execute("""
            SELECT * FROM dark_pool_metrics
            ORDER BY date DESC LIMIT 1
        """)
        darkpool_row = await darkpool_cursor.fetchone()
        darkpool_data = dict(darkpool_row) if darkpool_row else None

        # Fetch latest signal scores
        signal_cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 1
        """)
        signal_row = await signal_cursor.fetchone()
        signal_data = dict(signal_row) if signal_row else None
        signal_is_live = False
        if signal_data is None:
            # 方案 A: no persisted signal → live-compute the four dimension
            # scores so the dashboard cards never render empty. The synthetic
            # signal is NOT written to signal_alerts (keeps the alert history
            # clean); it only feeds the UI read.
            try:
                live = await _live_compute_signal(
                    gex_data, vix_data, crypto_data, darkpool_data,
                )
                if live is not None:
                    signal_data = live
                    signal_is_live = True
            except Exception:
                logger.exception("live-compute fallback failed")

    # FIX-01: aggregate mock-source set across dimensions from the DB-persisted
    # `is_mock` column (data_writer now propagates _meta.is_mock → DB column).
    # Previously this loop read `payload.get("_meta")` which was structurally
    # impossible — SQLite rows have no `_meta` key, so the UI never learned
    # which dimensions were mocked.
    mock_sources: set[str] = set()
    for source_name, payload in (
        ("gex", gex_data),
        ("vix", vix_data),
        ("crypto", crypto_data),
        ("darkpool", darkpool_data),
    ):
        if payload and isinstance(payload, dict):
            if payload.get("is_mock"):
                mock_sources.add(source_name)

    # Signal-level mock metadata (FIX-01: from signal_alerts.mock_sources / mock_count)
    signal_mock_sources: list[str] = []
    signal_mock_count: int = 0
    if signal_data and isinstance(signal_data, dict):
        raw_mock_sources = signal_data.get("mock_sources")
        if raw_mock_sources:
            try:
                # Stored as JSON list in the DB
                parsed = json.loads(raw_mock_sources) if isinstance(raw_mock_sources, str) else raw_mock_sources
                if isinstance(parsed, list):
                    signal_mock_sources = [str(x) for x in parsed]
            except (ValueError, TypeError):
                signal_mock_sources = []
        try:
            signal_mock_count = int(signal_data.get("mock_count") or 0)
        except (TypeError, ValueError):
            signal_mock_count = 0

    # Reconcile: union of dimension-level and signal-level mock sources
    combined_mock_sources = sorted(set(mock_sources) | set(signal_mock_sources))
    combined_mock_count = max(len(mock_sources), signal_mock_count, len(signal_mock_sources))

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "gex": gex_data,
        "vix": vix_data,
        "crypto": crypto_data,
        "darkpool": darkpool_data,
        "signal": signal_data,
        "_meta": {
            "mock_sources": combined_mock_sources,
            "mock_count": combined_mock_count,
            "signal_is_live": signal_is_live,
        },
    }


@router.get("/summary")
async def dashboard_summary():
    """Dashboard summary — high-level overview of system state."""
    async with get_db() as db:
        # Source health
        health_cursor = await db.execute("SELECT * FROM v_source_health")
        health_rows = await health_cursor.fetchall()
        source_health = [dict(r) for r in health_rows]

        # Signal summary
        sig_cursor = await db.execute("SELECT * FROM v_signal_summary")
        sig_rows = await sig_cursor.fetchall()
        signal_summary = [dict(r) for r in sig_rows]

        # Latest scores
        score_cursor = await db.execute("""
            SELECT total_score, alert_level, trigger_time
            FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 5
        """)
        score_rows = await score_cursor.fetchall()
        recent_scores = [dict(r) for r in score_rows]

    return {
        "source_health": source_health,
        "signal_summary": signal_summary,
        "recent_scores": recent_scores,
    }


@router.get("/signal-status")
async def signal_status():
    """Current signal status — latest alert level and dimension breakdown."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM v_resonance_dashboard
            ORDER BY trigger_time DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            return dict(row)

    return {
        "message": "No signals recorded yet",
        "total_score": 0.0,
        "alert_level": "NONE",
    }


@router.get("/scores")
async def dashboard_scores():
    """Current four-dimension resonance scores."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            return {
                "total_score": data.get("total_score"),
                "gex_score": data.get("gex_score"),
                "vix_score": data.get("vix_score"),
                "crypto_score": data.get("crypto_score"),
                "darkpool_score": data.get("darkpool_score"),
                "alert_level": data.get("alert_level"),
                "trigger_time": data.get("trigger_time"),
            }

    return {
        "total_score": 0.0,
        "gex_score": 0.0,
        "vix_score": 0.0,
        "crypto_score": 0.0,
        "darkpool_score": 0.0,
        "alert_level": "NONE",
    }


@router.get("/recent-alerts")
async def recent_alerts(
    limit: int = Query(10, ge=1, le=100),
):
    """Recent signal alerts."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM signal_alerts
            ORDER BY trigger_time DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/resonance-history")
async def resonance_history(
    days: int = Query(90, ge=1, le=365),
):
    """Resonance score history for charting."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT trigger_time, total_score, gex_score, vix_score,
                   crypto_score, darkpool_score, alert_level
            FROM signal_alerts
            WHERE trigger_time >= datetime('now', '-' || ? || ' days')
            ORDER BY trigger_time ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/cross-asset-heatmap")
async def cross_asset_heatmap():
    """Cross-asset correlation heatmap data."""
    async with get_db() as db:
        # Get latest dimension scores for heatmap
        cursor = await db.execute("""
            SELECT gex_score, vix_score, crypto_score, darkpool_score
            FROM signal_alerts
            ORDER BY trigger_time DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            return {
                "dimensions": {
                    "GEX": dict(row).get("gex_score", 0),
                    "VIX": dict(row).get("vix_score", 0),
                    "Crypto": dict(row).get("crypto_score", 0),
                    "Darkpool": dict(row).get("darkpool_score", 0),
                }
            }
    return {"dimensions": {"GEX": 0, "VIX": 0, "Crypto": 0, "Darkpool": 0}}


@router.get("/gex-curve")
async def gex_curve(
    days: int = Query(90, ge=1, le=365),
):
    """GEX long-term curve from SqueezeMetrics history."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM gex_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/multi-channel-curve")
async def multi_channel_curve(
    days: int = Query(90, ge=1, le=365),
):
    """Multi-channel curve (GEX + VEX + CHEX) — V2.5."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT timestamp, gex_local, gex_calibrated, alpha_factor
            FROM gex_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (days,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/data-quality")
async def data_quality():
    """Liquidity gate quality scores from source health view."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM v_source_health")
        rows = await cursor.fetchall()
        sources = [dict(r) for r in rows]

    total_sources = len(sources)
    # ponytail: age_minutes can be None (e.g. source with 0 rows / no data) — normalizing to a large number
    # avoids `TypeError: '<' not supported between NoneType and int` → HTTP 500 on /api/dashboard/data-quality
    def _age_minutes(s):
        v = s.get("age_minutes")
        return v if v is not None else 99999

    healthy_sources = sum(1 for s in sources if _age_minutes(s) < 1440)
    return {
        "total_sources": total_sources,
        "healthy_sources": healthy_sources,
        "quality_pct": round(healthy_sources / max(total_sources, 1) * 100, 1),
        "sources": sources,
        "mock_sources": [
            s.get("source") for s in sources
            if (s.get("is_mock") or s.get("mock_reason"))
        ],
    }


@router.get("/pipeline-metrics")
async def pipeline_metrics(request: Request):
    """Pipeline V2.0 runtime metrics."""
    pipeline = request.app.state.pipeline
    event_bus = request.app.state.event_bus
    return {
        "pipeline": pipeline.get_status(),
        "event_bus": event_bus.get_stats(),
    }
