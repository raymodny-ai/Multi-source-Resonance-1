"""
Pydantic models for GEX domain tables:
- gex_snapshots
- gex_strikes
- gex_history
- alpha_history
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── gex_snapshots ─────────────────────────────────────────────────────────────

class GEXSnapshotBase(BaseModel):
    symbol: str = Field(..., description="Ticker symbol (SPX/SPY/QQQ/IWM/NDX/VIX)")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    filename: str = Field(..., description="Original JSON filename")
    net_gex: Optional[float] = Field(None, description="Net Gamma Exposure")
    call_gex: Optional[float] = Field(None, description="Call GEX total")
    put_gex: Optional[float] = Field(None, description="Put GEX total (negative)")
    zero_gamma_level: Optional[float] = Field(None, description="Zero gamma price level")
    call_wall: Optional[float] = Field(None, description="Call Wall (max Call GEX strike)")
    put_wall: Optional[float] = Field(None, description="Put Wall (max Put GEX strike)")
    spot_price: Optional[float] = Field(None, description="Underlying spot price")
    total_gamma: Optional[float] = Field(None, description="Total gamma (|call_gex| + |put_gex|)")
    file_size: Optional[int] = Field(None, description="Original JSON file size in bytes")
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Data quality score (0-1)")
    data_lag_seconds: Optional[int] = Field(None, description="Data lag in seconds")
    oi_coverage_pct: Optional[float] = Field(None, ge=0, le=100, description="OI coverage percentage")


class GEXSnapshotCreate(GEXSnapshotBase):
    """Schema for creating a new GEX snapshot."""
    pass


class GEXSnapshot(GEXSnapshotBase):
    """Full GEX snapshot with id and created_at."""
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── gex_strikes ───────────────────────────────────────────────────────────────

class GEXStrikeBase(BaseModel):
    symbol: str
    timestamp: datetime
    strike: float = Field(..., description="Strike price")
    call_gex: float = Field(0, description="Call GEX at this strike ($)")
    put_gex: float = Field(0, description="Put GEX at this strike ($)")
    call_oi: int = Field(0, description="Call open interest")
    put_oi: int = Field(0, description="Put open interest")
    call_vol: int = Field(0, description="Call volume")
    put_vol: int = Field(0, description="Put volume")
    net_gex: float = Field(0, description="Net GEX at this strike (= call_gex + put_gex)")


class GEXStrikeCreate(GEXStrikeBase):
    snapshot_id: int = Field(..., description="FK to gex_snapshots.id")


class GEXStrike(GEXStrikeBase):
    id: int
    snapshot_id: int

    model_config = {"from_attributes": True}


# ── gex_history ───────────────────────────────────────────────────────────────

class GEXHistoryBase(BaseModel):
    timestamp: datetime
    gex_local: float
    gex_calibrated: Optional[float] = None
    alpha_factor: Optional[float] = None
    put_wall_level: Optional[float] = None
    flip_zone_lower: Optional[float] = None
    flip_zone_upper: Optional[float] = None


class GEXHistory(GEXHistoryBase):
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── alpha_history ─────────────────────────────────────────────────────────────

class AlphaHistoryBase(BaseModel):
    timestamp: datetime
    symbol: str = "SPX"
    alpha_raw: Optional[float] = None
    alpha_ewm_20d: Optional[float] = None
    alpha_ewm_60d: Optional[float] = None
    gex_metrix_net: Optional[float] = None
    gex_squeeze_net: Optional[float] = None


class AlphaHistory(AlphaHistoryBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
