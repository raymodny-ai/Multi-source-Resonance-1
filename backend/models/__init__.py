"""
Pydantic data models for the Multi-source Resonance Monitoring System.
Re-exports all models for convenient access.
"""

# GEX domain
from backend.models.gex import (
    AlphaHistory,
    AlphaHistoryBase,
    GEXHistory,
    GEXHistoryBase,
    GEXSnapshot,
    GEXSnapshotBase,
    GEXSnapshotCreate,
    GEXStrike,
    GEXStrikeBase,
    GEXStrikeCreate,
)

# VIX domain
from backend.models.vix import VIXSnapshot, VIXSnapshotBase, VIXSnapshotCreate

# Crypto domain
from backend.models.crypto import CryptoSignal, CryptoSignalBase, CryptoSignalCreate

# Darkpool domain
from backend.models.darkpool import DarkpoolFlow, DarkpoolFlowBase, DarkpoolFlowCreate

# Signal & alert domain
from backend.models.signal import SignalAlert, SignalAlertBase, SignalAlertCreate, SignalAcknowledge

# System domain
from backend.models.system import (
    APIKey,
    APIKeyBase,
    APIKeyCreate,
    GatewaySnapshot,
    GatewaySnapshotBase,
    SystemConfig,
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    ValidationAudit,
    ValidationAuditBase,
)

# Common / shared
from backend.models.common import (
    APIResponse,
    ErrorResponse,
    HealthCheck,
    PaginatedResponse,
    SourceStatus,
    SystemStatus,
)

__all__ = [
    # GEX
    "GEXSnapshot", "GEXSnapshotBase", "GEXSnapshotCreate",
    "GEXStrike", "GEXStrikeBase", "GEXStrikeCreate",
    "GEXHistory", "GEXHistoryBase",
    "AlphaHistory", "AlphaHistoryBase",
    # VIX
    "VIXSnapshot", "VIXSnapshotBase", "VIXSnapshotCreate",
    # Crypto
    "CryptoSignal", "CryptoSignalBase", "CryptoSignalCreate",
    # Darkpool
    "DarkpoolFlow", "DarkpoolFlowBase", "DarkpoolFlowCreate",
    # Signals
    "SignalAlert", "SignalAlertBase", "SignalAlertCreate", "SignalAcknowledge",
    # System
    "SystemConfig", "SystemConfigBase", "SystemConfigCreate", "SystemConfigUpdate",
    "ValidationAudit", "ValidationAuditBase",
    "GatewaySnapshot", "GatewaySnapshotBase",
    "APIKey", "APIKeyBase", "APIKeyCreate",
    # Common
    "HealthCheck", "PaginatedResponse", "APIResponse", "ErrorResponse",
    "SourceStatus", "SystemStatus",
]
