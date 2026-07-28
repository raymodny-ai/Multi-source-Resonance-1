"""
Pydantic models for dark_pool_metrics table.
"""

from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── dark_pool_metrics ─────────────────────────────────────────────────────────

class DarkpoolFlowBase(BaseModel):
    date: date_type = Field(..., description="Metrics date")
    dix_value: Optional[float] = Field(None, description="Dark Index (DIX) value")
    chartexchange_short_ratio: Optional[float] = Field(None, description="ChartExchange short ratio")
    stockgrid_20d_slope: Optional[float] = Field(None, description="20-day price slope")
    stockgrid_60d_slope: Optional[float] = Field(None, description="60-day price slope")
    stockgrid_divergence: Optional[bool] = Field(None, description="Price/volume divergence flag")
    dbmf_ma5_recovery: Optional[bool] = Field(None, description="MA5 recovery flag")
    dix_signal: Optional[bool] = None
    short_ratio_signal: Optional[bool] = None
    stockgrid_signal: Optional[bool] = None
    aggregated_signal: Optional[bool] = None
    v_net: Optional[float] = Field(None, description="Net short volume")
    ema_fast_5: Optional[float] = Field(None, description="EMA 5-day (V_Net)")
    ema_slow_20: Optional[float] = Field(None, description="EMA 20-day")
    zero_cross_signal: Optional[str] = Field(None, description="'bullish_cross' | 'bearish_cross'")
    momentum_reversal_signal: Optional[str] = None


class DarkpoolFlowCreate(DarkpoolFlowBase):
    pass


class DarkpoolFlow(DarkpoolFlowBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
