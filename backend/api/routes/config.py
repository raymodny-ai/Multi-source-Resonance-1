"""
Configuration management API routes.
Provides endpoints for reading/updating system_config and data source configuration.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.database import get_db
from backend.eventbus.events import EventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get("")
async def get_config():
    """Get current system configuration from system_config table."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM system_config ORDER BY key")
        rows = await cursor.fetchall()
        configs = [dict(r) for r in rows]

    return {
        "configs": configs,
        "count": len(configs),
    }


@router.put("")
async def update_config(request: Request):
    """Update system configuration (requires JWT).

    Accepts JSON body: {"key": "value", "description": "optional"}
    Writes to system_config and broadcasts CONFIG change event.
    """
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    description = body.get("description")

    if not key or value is None:
        raise HTTPException(status_code=400, detail="'key' and 'value' are required")

    async with get_db() as db:
        # Check if key exists
        cursor = await db.execute(
            "SELECT key FROM system_config WHERE key = ?", (key,)
        )
        existing = await cursor.fetchone()

        now = datetime.now(timezone.utc).isoformat()
        if existing:
            await db.execute(
                "UPDATE system_config SET value = ?, description = COALESCE(?, description), updated_at = ? WHERE key = ?",
                (value, description, now, key),
            )
        else:
            await db.execute(
                "INSERT INTO system_config (key, value, description, updated_at) VALUES (?, ?, ?, ?)",
                (key, value, description, now),
            )

    # Broadcast config change via EventBus
    event_bus = request.app.state.event_bus
    await event_bus.publish(EventType.SYSTEM_CONFIG_CHANGE, {
        "key": key,
        "value": value,
        "updated_at": now,
    })

    logger.info(f"Config updated: {key} = {value}")
    return {"ok": True, "key": key, "value": value}


@router.get("/defaults")
async def get_defaults():
    """Get default configuration values."""
    return {
        "alpha_factor": "1.0",
        "gex_threshold": "35000000",
        "alert_level_3_min": "3.5",
        "fetch_interval_seconds": 60,
        "max_workers": 8,
    }


@router.get("/sources")
async def get_sources():
    """Get data source configuration list."""
    from backend.config import settings

    sources = [
        {
            "name": "GEXMetrix",
            "enabled": True,
            "has_api_key": bool(settings.gexmetrix_api_key),
            "mock_mode": settings.is_mock_mode("gexmetrix"),
        },
        {
            "name": "AXLFI",
            "enabled": True,
            "has_api_key": bool(settings.axlfi_api_key),
            "mock_mode": settings.is_mock_mode("axlfi"),
        },
        {
            "name": "Crypto",
            "enabled": True,
            "has_api_key": bool(settings.crypto_api_key),
            "mock_mode": settings.is_mock_mode("crypto"),
        },
        {
            "name": "Darkpool",
            "enabled": True,
            "has_api_key": bool(settings.darkpool_api_key),
            "mock_mode": settings.is_mock_mode("darkpool"),
        },
        {
            "name": "VIX (CBOE)",
            "enabled": True,
            "has_api_key": False,
            "mock_mode": False,
        },
        {
            "name": "yfinance",
            "enabled": True,
            "has_api_key": False,
            "mock_mode": False,
        },
    ]
    return sources


@router.put("/sources/{name}")
async def update_source_config(name: str, request: Request):
    """Update data source configuration (requires JWT).

    Accepts JSON body: {"enabled": true/false, "api_key": "optional"}
    """
    body = await request.json()
    # Currently we only support runtime toggling; API key changes require restart
    enabled = body.get("enabled")

    if enabled is not None:
        async with get_db() as db:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO system_config (key, value, description, updated_at) VALUES (?, ?, ?, ?)",
                (f"source_{name.lower()}_enabled", str(enabled).lower(), f"Enable/disable {name} data source", now),
            )

    return {"ok": True, "source": name, "enabled": enabled}


@router.get("/audit")
async def config_audit():
    """Configuration change audit log (from gateway_snapshots with source='config_change')."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM gateway_snapshots
            WHERE source = 'config_change'
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.post("/restore")
async def restore_defaults(request: Request):
    """Restore configuration to defaults (requires JWT)."""
    defaults = {
        "alpha_factor": ("1.0", "GEX calibration coefficient"),
        "gex_threshold": ("35000000", "GEX threshold value (35M)"),
        "alert_level_3_min": ("75", "Minimum score for LEVEL_3 alert (normalized 0-100)"),
    }

    async with get_db() as db:
        now = datetime.now(timezone.utc).isoformat()
        for key, (value, desc) in defaults.items():
            await db.execute(
                "INSERT OR REPLACE INTO system_config (key, value, description, updated_at) VALUES (?, ?, ?, ?)",
                (key, value, desc, now),
            )

    # Broadcast config change
    event_bus = request.app.state.event_bus
    await event_bus.publish(EventType.SYSTEM_CONFIG_CHANGE, {
        "action": "restore_defaults",
        "updated_at": now,
    })

    logger.info("Configuration restored to defaults")
    return {"ok": True, "message": "Configuration restored to defaults"}


# ── Bayesian weight management ───────────────────────────────────────────────


@router.get("/weights")
async def get_weights():
    """Return current dimension weights (default or Bayesian-adapted)."""
    from backend.quant.scoring import get_current_weights, DEFAULT_WEIGHTS, RAW_MAX
    from backend.quant.bayesian_weights import BayesianWeightAdapter

    current = get_current_weights()
    is_adapted = current != DEFAULT_WEIGHTS

    # Gather adapter stats if available
    try:
        from backend.quant.scoring import _get_adapter
        adapter = _get_adapter()
        adapter_stats = adapter.get_update_stats()
        posterior_summary = adapter.get_posterior_summary()
    except Exception:
        adapter_stats = None
        posterior_summary = None

    return {
        "weights": current,
        "default_weights": DEFAULT_WEIGHTS,
        "raw_max": RAW_MAX,
        "is_adapted": is_adapted,
        "adapter_stats": adapter_stats,
        "posterior_summary": posterior_summary,
    }


@router.post("/weights/reset")
async def reset_weights():
    """Reset dimension weights to defaults (requires JWT)."""
    from backend.quant.scoring import reset_weights, DEFAULT_WEIGHTS

    reset_weights()
    logger.info("Weights reset to defaults via API")
    return {
        "ok": True,
        "message": "Weights reset to defaults",
        "weights": DEFAULT_WEIGHTS,
    }
