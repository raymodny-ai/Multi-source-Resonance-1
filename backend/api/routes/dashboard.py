"""
Dashboard BFF (Backend-For-Frontend) aggregation routes.
Provides single-call endpoints that aggregate data from multiple dimensions.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


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

    # Aggregate the mock-source set across dimensions for the UI to surface.
    mock_sources: set[str] = set()
    for source_name, payload in (
        ("gex", gex_data),
        ("vix", vix_data),
        ("crypto", crypto_data),
        ("darkpool", darkpool_data),
    ):
        if payload and isinstance(payload, dict):
            meta = payload.get("_meta") or {}
            if meta.get("is_mock"):
                mock_sources.add(source_name)

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "gex": gex_data,
        "vix": vix_data,
        "crypto": crypto_data,
        "darkpool": darkpool_data,
        "signal": signal_data,
        "_meta": {
            "mock_sources": sorted(mock_sources),
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
    healthy_sources = sum(1 for s in sources if s.get("age_minutes", 9999) < 1440)
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
