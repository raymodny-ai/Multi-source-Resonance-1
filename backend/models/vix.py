"""
Pydantic models for vix_analysis table.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VIXSnapshotBase(BaseModel):
    timestamp: str = Field(..., description="VIX data timestamp")
    vix_spot: Optional[float] = Field(None, description="VIX spot price")
    vx1: Optional[float] = Field(None, description="VIX 1-month futures")
    vx2: Optional[float] = Field(None, description="VIX 2-month futures")
    term_structure_ratio: Optional[float] = Field(None, description="(vx2/vx1) - 1")
    term_structure_state: Optional[str] = Field(None, description="'contango' | 'backwardation' | 'flat'")
    panic_premium: Optional[float] = Field(None, description="Panic premium value")


class VIXSnapshotCreate(VIXSnapshotBase):
    pass


class VIXSnapshot(VIXSnapshotBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
