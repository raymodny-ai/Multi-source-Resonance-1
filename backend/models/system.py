"""
Pydantic models for system_config, validation_audit_log, gateway_snapshots tables.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── system_config ─────────────────────────────────────────────────────────────

class SystemConfigBase(BaseModel):
    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Human-readable description")


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfig(SystemConfigBase):
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SystemConfigUpdate(BaseModel):
    """Schema for updating a config value."""
    value: str
    description: Optional[str] = None


# ── validation_audit_log ─────────────────────────────────────────────────────

class ValidationAuditBase(BaseModel):
    timestamp: datetime
    source: str = Field(..., description="Data source name")
    symbol: Optional[str] = None
    check_type: str = Field(..., description="Validation check category")
    check_name: str = Field(..., description="Specific check name")
    passed: bool
    input_value: Optional[str] = None
    expected_range: Optional[str] = None
    severity: str = Field("INFO", description="'INFO' | 'WARN' | 'ERROR'")
    message: Optional[str] = None
    raw_data_hash: Optional[str] = None
    retry_count: int = 0


class ValidationAudit(ValidationAuditBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── gateway_snapshots ─────────────────────────────────────────────────────────

class GatewaySnapshotBase(BaseModel):
    timestamp: datetime
    source: str = Field(..., description="Data source name")
    payload_hash: Optional[str] = None
    payload_size: Optional[int] = None
    layer1_output: Optional[str] = Field(None, description="Layer1 math output JSON")
    layer2_output: Optional[str] = Field(None, description="Layer2 gateway output JSON")
    status: str = Field("OK", description="Processing status")
    error_message: Optional[str] = None


class GatewaySnapshot(GatewaySnapshotBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── API Keys (for auth management) ───────────────────────────────────────────

class APIKeyBase(BaseModel):
    name: str = Field(..., description="API key name/label")
    key: str = Field(..., description="API key value")
    source: str = Field(..., description="Data source this key belongs to")


class APIKeyCreate(APIKeyBase):
    pass


class APIKey(APIKeyBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
