"""
Common / shared Pydantic models: pagination, health check, API responses.
"""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Health Check ──────────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    """GET /api/health response."""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "3.1.0"
    uptime_seconds: float = 0.0


# ── Paginated Response ────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int = Field(..., description="Total item count")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    pages: int = Field(0, description="Total number of pages")


# ── Generic API Response ──────────────────────────────────────────────────────

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = "ok"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response body."""
    success: bool = False
    message: str
    detail: Optional[str] = None


# ── Source Status ─────────────────────────────────────────────────────────────

class SourceStatus(BaseModel):
    """Data source connectivity status."""
    name: str
    status: str = Field(..., description="'online' | 'degraded' | 'offline'")
    method: str = Field(..., description="Fetch method description")
    availability_pct: float = Field(100.0, ge=0, le=100)
    last_error: Optional[str] = None
    last_success_at: Optional[datetime] = None


# ── System Status ─────────────────────────────────────────────────────────────

class SystemStatus(BaseModel):
    """GET /api/status response — CPU / memory / connection info."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    db_size_mb: float
    active_connections: int
    uptime_seconds: float
