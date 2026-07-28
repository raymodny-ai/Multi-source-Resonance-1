"""
Pydantic models for signal_alerts table.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SignalAlertBase(BaseModel):
    trigger_time: datetime = Field(..., description="Signal trigger time")
    total_score: float = Field(..., ge=0, le=5.0, description="Total resonance score (0-5.0)")
    gex_score: Optional[float] = Field(None, description="GEX dimension contribution (0-2.5)")
    vix_score: Optional[float] = Field(None, description="VIX dimension contribution (0-1.5)")
    crypto_score: Optional[float] = Field(None, description="Crypto dimension contribution (0-2.0)")
    darkpool_score: Optional[float] = Field(None, description="Darkpool dimension contribution (0-2.0)")
    alert_level: str = Field(..., description="'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3'")
    hawkes_branching_ratio: Optional[float] = Field(None, ge=0, le=1, description="Hawkes self-exciting branching ratio")
    details: Optional[str] = Field(None, description="JSON details")
    acknowledged: bool = Field(False, description="Whether alert has been acknowledged")
    outcome: Optional[str] = Field(None, description="Signal outcome: 'profit' / 'loss' / NULL")
    forward_return: Optional[float] = Field(None, description="Actual return after signal trigger (N-day)")
    outcome_checked_at: Optional[str] = Field(None, description="Timestamp when outcome was evaluated")


class SignalAlertCreate(SignalAlertBase):
    pass


class SignalAlert(SignalAlertBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SignalAcknowledge(BaseModel):
    """Schema for acknowledging a signal alert."""
    acknowledged: bool = True
