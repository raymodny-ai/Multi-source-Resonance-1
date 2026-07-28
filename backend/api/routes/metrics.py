"""
Monitoring metrics API routes.
Provides Prometheus-format metrics and JSON summary endpoints.
"""

import logging
import os
import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


@router.get("", response_class=PlainTextResponse)
async def prometheus_metrics(request: Request):
    """Prometheus-format metrics endpoint.

    Returns metrics in Prometheus text exposition format:
    - Collection timing
    - Signal counts
    - Database size
    - Memory usage
    """
    pipeline = request.app.state.pipeline
    event_bus = request.app.state.event_bus

    # Gather metrics
    db_path = pipeline.config.db_absolute_path
    db_size_bytes = db_path.stat().st_size if db_path.exists() else 0

    lines = [
        "# HELP resonance_info System information",
        "# TYPE resonance_info gauge",
        'resonance_info{version="3.1.0"} 1',
        "",
        "# HELP resonance_uptime_seconds Uptime in seconds",
        "# TYPE resonance_uptime_seconds gauge",
    ]

    # Uptime
    start_time = getattr(request.app.state, '_start_time', time.time())
    uptime = time.time() - start_time
    lines.append(f"resonance_uptime_seconds {uptime:.2f}")
    lines.append("")

    # Pipeline metrics
    status = pipeline.get_status()
    lines.extend([
        "# HELP resonance_pipeline_running Whether pipeline is running",
        "# TYPE resonance_pipeline_running gauge",
        f"resonance_pipeline_running {1 if status['running'] else 0}",
        "",
        "# HELP resonance_pipeline_cycles_total Total pipeline cycles",
        "# TYPE resonance_pipeline_cycles_total counter",
        f"resonance_pipeline_cycles_total {status['cycle_count']}",
        "",
        "# HELP resonance_fetcher_count Number of configured fetchers",
        "# TYPE resonance_fetcher_count gauge",
        f"resonance_fetcher_count {status['fetcher_count']}",
        "",
    ])

    # EventBus metrics
    eb_stats = event_bus.get_stats()
    lines.extend([
        "# HELP resonance_events_published_total Total events published",
        "# TYPE resonance_events_published_total counter",
        f"resonance_events_published_total {eb_stats['total_published']}",
        "",
        "# HELP resonance_events_errors_total Total event handler errors",
        "# TYPE resonance_events_errors_total counter",
        f"resonance_events_errors_total {eb_stats['total_errors']}",
        "",
    ])

    # Database metrics
    lines.extend([
        "# HELP resonance_db_size_bytes Database file size in bytes",
        "# TYPE resonance_db_size_bytes gauge",
        f"resonance_db_size_bytes {db_size_bytes}",
        "",
    ])

    # Table row counts
    async with get_db() as db:
        tables = [
            "gex_snapshots", "gex_strikes", "gex_history", "vix_analysis",
            "dark_pool_metrics", "crypto_derivatives", "signal_alerts",
        ]
        for table in tables:
            try:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                row = await cursor.fetchone()
                count = row[0] if row else 0
            except Exception:
                count = 0
            lines.append(f"resonance_db_rows{{table=\"{table}\"}} {count}")

    lines.append("")

    # Signal counts by level
    async with get_db() as db:
        try:
            cursor = await db.execute("""
                SELECT alert_level, COUNT(*) as cnt
                FROM signal_alerts
                GROUP BY alert_level
            """)
            rows = await cursor.fetchall()
            for row in rows:
                level = row["alert_level"]
                cnt = row["cnt"]
                lines.append(f"resonance_signals_total{{level=\"{level}\"}} {cnt}")
        except Exception:
            pass

    lines.append("")

    # Memory usage
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        lines.extend([
            "# HELP resonance_process_memory_bytes Process memory in bytes",
            "# TYPE resonance_process_memory_bytes gauge",
            f"resonance_process_memory_bytes {mem.rss}",
            "",
        ])
    except ImportError:
        pass

    return "\n".join(lines)


@router.get("/summary")
async def metrics_summary(request: Request):
    """JSON metrics summary — human-readable system metrics."""
    pipeline = request.app.state.pipeline
    event_bus = request.app.state.event_bus

    db_path = pipeline.config.db_absolute_path
    db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0

    start_time = getattr(request.app.state, '_start_time', time.time())
    uptime = round(time.time() - start_time, 2)

    # Table counts
    table_counts = {}
    async with get_db() as db:
        tables = [
            "gex_snapshots", "gex_strikes", "gex_history", "vix_analysis",
            "dark_pool_metrics", "crypto_derivatives", "signal_alerts",
        ]
        for table in tables:
            try:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                row = await cursor.fetchone()
                table_counts[table] = row[0] if row else 0
            except Exception:
                table_counts[table] = 0

    return {
        "uptime_seconds": uptime,
        "pipeline": {
            "running": pipeline.is_running,
            "cycles": pipeline.cycle_count,
            "fetchers": len(pipeline.fetchers),
        },
        "event_bus": event_bus.get_stats(),
        "database": {
            "size_mb": db_size_mb,
            "table_counts": table_counts,
        },
    }
