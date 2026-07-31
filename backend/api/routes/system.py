"""
System control API routes.
Provides endpoints for system status, pipeline control, logs, and source status.
"""

import logging
import os
import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from backend.database import get_db
from backend.eventbus.events import EventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System"])

# In-memory log buffer for recent system events
_system_logs: list[dict] = []
_MAX_LOGS = 500


def add_system_log(level: str, message: str, source: str = "system") -> None:
    """Add an entry to the in-memory system log buffer."""
    _system_logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "message": message,
    })
    if len(_system_logs) > _MAX_LOGS:
        _system_logs.pop(0)


@router.get("/status")
async def system_status(request: Request):
    """System status — CPU, memory, DB size, connections, uptime."""
    import psutil

    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    db_path = request.app.state.pipeline.config.db_absolute_path

    db_size_mb = 0.0
    if db_path.exists():
        db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)

    uptime = time.time() - request.app.state._start_time if hasattr(request.app.state, '_start_time') else 0.0

    return {
        "cpu_percent": process.cpu_percent(),
        "memory_percent": process.memory_percent(),
        "memory_used_mb": round(mem_info.rss / (1024 * 1024), 2),
        "memory_total_mb": round(psutil.virtual_memory().total / (1024 * 1024), 2),
        "db_size_mb": db_size_mb,
        "active_connections": 0,  # WebSocket connections tracked separately
        "uptime_seconds": round(uptime, 2),
        "python_version": platform.python_version(),
        "platform": platform.system(),
    }


@router.get("/source-status")
async def source_status():
    """Data source connectivity status from v_source_health view.

    The pipeline's last cycle report (when available) overlays ``is_mock``,
    ``mock_reason`` and ``last_error`` so the UI can flag degraded sources.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM v_source_health")
        rows = await cursor.fetchall()
        sources = [dict(r) for r in rows]

    # Per-source overlay from the latest pipeline cycle, if any.
    per_source_state: dict[str, dict] = {}
    try:
        from backend.main import app as _app  # local import to avoid cycles
        pipeline = getattr(_app.state, "pipeline", None)
        last_report = getattr(pipeline, "last_report", None) if pipeline else None
        if last_report:
            for detail in last_report.get("source_details", []) or []:
                per_source_state[detail["source"].lower()] = detail
    except Exception:
        per_source_state = {}

    # Map to standard SourceStatus format
    result = []
    for src in sources:
        name = src.get("source") or ""
        age_minutes = src.get("age_minutes") or 9999
        status = "online" if age_minutes < 1440 else ("degraded" if age_minutes < 4320 else "offline")
        overlay = per_source_state.get(name.lower(), {})
        result.append({
            "name": name,
            "status": status,
            "method": "REST API",
            "availability_pct": round(max(0, 100 - (age_minutes / 1440 * 100)), 1) if age_minutes < 1440 else 0.0,
            "last_data_ts": src.get("last_data_ts"),
            "total_rows": src.get("total_rows"),
            "age_minutes": round(age_minutes, 1),
            "last_error": overlay.get("error"),
            "is_mock": bool(overlay.get("is_mock", False)),
            "mock_reason": overlay.get("mock_reason"),
            "retry_count": int(overlay.get("retry_count", 0) or 0),
        })

    return result


@router.get("/logs")
async def system_logs(
    limit: int = Query(50, ge=1, le=500, description="Number of recent log entries"),
):
    """Recent system logs (in-memory buffer)."""
    return _system_logs[-limit:]


@router.get("/auto-polling")
async def get_auto_polling(request: Request):
    """Current auto-polling state."""
    pipeline = request.app.state.pipeline
    return {
        "enabled": pipeline.is_running,
        "interval_seconds": pipeline.config.fetch_interval_second,
    }


@router.put("/auto-polling")
async def set_auto_polling(request: Request):
    """Toggle auto-polling on/off (requires JWT)."""
    body = await request.json()
    enabled = body.get("enabled", True)
    pipeline = request.app.state.pipeline

    if enabled and not pipeline.is_running:
        pipeline.start_background()
        return {"enabled": True, "message": "Auto-polling started"}
    elif not enabled and pipeline.is_running:
        await pipeline.stop()
        return {"enabled": False, "message": "Auto-polling stopped"}
    else:
        return {
            "enabled": pipeline.is_running,
            "message": "No change needed",
        }


@router.post("/collect-manual")
async def collect_manual(request: Request):
    """Manually trigger a full 8-dimension data collection cycle (requires JWT).

    Runs the pipeline once and returns the collection report.
    """
    pipeline = request.app.state.pipeline

    if pipeline.is_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running. Wait for current cycle to complete.",
        )

    try:
        add_system_log("INFO", "Manual collection triggered", source="api")
        report = await pipeline.run_cycle()
        add_system_log("INFO", f"Manual collection complete: {report.get('success_count')} sources", source="api")

        source_details = report.get("source_details", []) or []
        mock_count = report.get("mock_count", 0)
        return {
            "ok": True,
            "collected_at": report.get("cycle_ts"),
            "total_elapsed_sec": report.get("total_elapsed_sec"),
            "success_count": report.get("success_count"),
            "error_count": report.get("error_count"),
            "mock_count": mock_count,
            "sources": source_details,
            "write_results": report.get("write_results", {}),
        }
    except Exception as e:
        logger.error(f"Manual collection failed: {e}", exc_info=True)
        add_system_log("ERROR", f"Manual collection failed: {e}", source="api")
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")


@router.get("/collection-detail")
async def collection_detail(request: Request):
    """Return per-source details from the most recent pipeline cycle.

    Shape mirrors the ``source_details`` array published by the pipeline.
    Returns an empty list if the pipeline has not completed a cycle yet.
    """
    pipeline = request.app.state.pipeline
    last_report = getattr(pipeline, "last_report", None) or {}
    return {
        "cycle_ts": last_report.get("cycle_ts"),
        "cycle_number": last_report.get("cycle_number", 0),
        "success_count": last_report.get("success_count", 0),
        "error_count": last_report.get("error_count", 0),
        "mock_count": last_report.get("mock_count", 0),
        "sources": last_report.get("source_details", []) or [],
        "write_results": last_report.get("write_results", {}),
    }
