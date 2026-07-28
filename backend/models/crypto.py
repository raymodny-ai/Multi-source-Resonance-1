"""
Pydantic models for crypto_derivatives table.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CryptoSignalBase(BaseModel):
    timestamp: datetime
    btc_funding_rate: float = Field(..., description="BTC funding rate")
    btc_oi: Optional[float] = Field(None, description="BTC open interest")
    oi_change_1h: Optional[float] = Field(None, description="1h OI change rate")
    liquidation_spike: Optional[bool] = Field(None, description="Liquidation spike flag")
    cryptoquant_elr: Optional[float] = Field(None, description="Estimated Leverage Ratio")
    funding_anomaly: Optional[bool] = Field(None, description="Funding anomaly flag")
    oi_crash: Optional[bool] = Field(None, description="OI crash flag")
    leverage_cleanup: Optional[bool] = Field(None, description="Leverage cleanup signal")


class CryptoSignalCreate(CryptoSignalBase):
    pass


class CryptoSignal(CryptoSignalBase):
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
