"""
Unit tests for all Pydantic models: serialization, deserialization,
required/optional fields, and field validation.
"""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError


# ===========================================================================
# Common models
# ===========================================================================

class TestHealthCheckModel:
    from backend.models.common import HealthCheck

    def test_default_values(self):
        from backend.models.common import HealthCheck
        hc = HealthCheck()
        assert hc.status == "ok"
        assert hc.version == "3.1.0"
        assert hc.uptime_seconds == 0.0
        assert hc.timestamp is not None

    def test_custom_values(self):
        from backend.models.common import HealthCheck
        hc = HealthCheck(status="degraded", uptime_seconds=123.45)
        assert hc.status == "degraded"
        assert hc.uptime_seconds == 123.45

    def test_serialization(self):
        from backend.models.common import HealthCheck
        hc = HealthCheck()
        data = hc.model_dump()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestAPIResponseModel:
    def test_default_success(self):
        from backend.models.common import APIResponse
        resp = APIResponse()
        assert resp.success is True
        assert resp.message == "ok"

    def test_error_response(self):
        from backend.models.common import ErrorResponse
        resp = ErrorResponse(message="Not found", detail="Resource X missing")
        assert resp.success is False
        assert resp.message == "Not found"
        assert resp.detail is not None


class TestPaginatedResponseModel:
    def test_basic_pagination(self):
        from backend.models.common import PaginatedResponse
        resp = PaginatedResponse[str](
            items=["a", "b", "c"],
            total=30,
            page=1,
            page_size=10,
            pages=3,
        )
        assert len(resp.items) == 3
        assert resp.total == 30
        assert resp.pages == 3

    def test_page_ge_1(self):
        from backend.models.common import PaginatedResponse
        with pytest.raises(ValidationError):
            PaginatedResponse[int](items=[], total=0, page=0, page_size=10, pages=0)


class TestSourceStatusModel:
    def test_required_fields(self):
        from backend.models.common import SourceStatus
        ss = SourceStatus(name="GEXMetrix", status="online", method="API")
        assert ss.availability_pct == 100.0
        assert ss.last_error is None

    def test_availability_bounded(self):
        from backend.models.common import SourceStatus
        with pytest.raises(ValidationError):
            SourceStatus(name="X", status="online", method="API", availability_pct=150)


class TestSystemStatusModel:
    def test_all_fields(self):
        from backend.models.common import SystemStatus
        ss = SystemStatus(
            cpu_percent=25.0,
            memory_percent=60.0,
            memory_used_mb=2048.0,
            memory_total_mb=4096.0,
            db_size_mb=100.0,
            active_connections=5,
            uptime_seconds=3600.0,
        )
        assert ss.cpu_percent == 25.0
        assert ss.active_connections == 5


# ===========================================================================
# GEX models
# ===========================================================================

class TestGEXSnapshotModel:
    def test_create_requires_symbol_timestamp_filename(self):
        from backend.models.gex import GEXSnapshotCreate
        snap = GEXSnapshotCreate(
            symbol="SPX",
            timestamp=datetime.now(timezone.utc),
            filename="test.json",
        )
        assert snap.symbol == "SPX"
        assert snap.net_gex is None  # optional

    def test_missing_required_field(self):
        from backend.models.gex import GEXSnapshotCreate
        with pytest.raises(ValidationError):
            GEXSnapshotCreate(symbol="SPX")  # missing timestamp, filename

    def test_quality_score_bounded(self):
        from backend.models.gex import GEXSnapshotCreate
        with pytest.raises(ValidationError):
            GEXSnapshotCreate(
                symbol="SPX",
                timestamp=datetime.now(timezone.utc),
                filename="test.json",
                quality_score=1.5,  # > 1
            )

    def test_full_snapshot_with_id(self):
        from backend.models.gex import GEXSnapshot
        snap = GEXSnapshot(
            id=1,
            symbol="SPX",
            timestamp=datetime.now(timezone.utc),
            filename="test.json",
            net_gex=1e9,
        )
        assert snap.id == 1


class TestGEXStrikeModel:
    def test_create_strike(self):
        from backend.models.gex import GEXStrikeCreate
        strike = GEXStrikeCreate(
            snapshot_id=1,
            symbol="SPX",
            timestamp=datetime.now(timezone.utc),
            strike=5750.0,
            call_gex=5e7,
            put_gex=-6e7,
        )
        assert strike.strike == 5750.0
        assert strike.net_gex == 0  # default

    def test_strike_with_id(self):
        from backend.models.gex import GEXStrike
        strike = GEXStrike(
            id=10,
            snapshot_id=1,
            symbol="SPX",
            timestamp=datetime.now(timezone.utc),
            strike=5750.0,
        )
        assert strike.id == 10


class TestGEXHistoryModel:
    def test_basic(self):
        from backend.models.gex import GEXHistory
        h = GEXHistory(
            timestamp=datetime.now(timezone.utc),
            gex_local=1e9,
        )
        assert h.gex_calibrated is None


class TestAlphaHistoryModel:
    def test_default_symbol(self):
        from backend.models.gex import AlphaHistoryBase
        ah = AlphaHistoryBase(timestamp=datetime.now(timezone.utc))
        assert ah.symbol == "SPX"


# ===========================================================================
# VIX models
# ===========================================================================

class TestVIXSnapshotModel:
    def test_create(self):
        from backend.models.vix import VIXSnapshotCreate
        v = VIXSnapshotCreate(
            timestamp="2025-01-01T00:00:00Z",
            vix_spot=15.5,
            vx1=16.0,
            vx2=17.0,
        )
        assert v.vix_spot == 15.5

    def test_full_with_id(self):
        from backend.models.vix import VIXSnapshot
        v = VIXSnapshot(
            id=1,
            timestamp="2025-01-01T00:00:00Z",
            vix_spot=15.5,
        )
        assert v.id == 1


# ===========================================================================
# Crypto models
# ===========================================================================

class TestCryptoSignalModel:
    def test_create(self):
        from backend.models.crypto import CryptoSignalCreate
        c = CryptoSignalCreate(
            timestamp=datetime.now(timezone.utc),
            btc_funding_rate=0.0001,
        )
        assert c.btc_funding_rate == 0.0001
        assert c.btc_oi is None

    def test_full_signal(self):
        from backend.models.crypto import CryptoSignal
        c = CryptoSignal(
            timestamp=datetime.now(timezone.utc),
            btc_funding_rate=0.001,
            btc_oi=22000.0,
            liquidation_spike=True,
        )
        assert c.liquidation_spike is True


# ===========================================================================
# Darkpool models
# ===========================================================================

class TestDarkpoolFlowModel:
    def test_create(self):
        from backend.models.darkpool import DarkpoolFlowCreate
        d = DarkpoolFlowCreate(
            date=date.today(),
            dix_value=52.0,
        )
        assert d.dix_value == 52.0

    def test_full_flow(self):
        from backend.models.darkpool import DarkpoolFlow
        d = DarkpoolFlow(
            date=date.today(),
            dix_value=55.0,
            aggregated_signal=True,
        )
        assert d.aggregated_signal is True


# ===========================================================================
# Signal models
# ===========================================================================

class TestSignalAlertModel:
    def test_create(self):
        from backend.models.signal import SignalAlertCreate
        s = SignalAlertCreate(
            trigger_time=datetime.now(timezone.utc),
            total_score=3.5,
            alert_level="LEVEL_2",
        )
        assert s.total_score == 3.5
        assert s.acknowledged is False

    def test_score_bounds(self):
        from backend.models.signal import SignalAlertCreate
        with pytest.raises(ValidationError):
            SignalAlertCreate(
                trigger_time=datetime.now(timezone.utc),
                total_score=6.0,  # > 5.0
                alert_level="LEVEL_3",
            )

    def test_negative_score_rejected(self):
        from backend.models.signal import SignalAlertCreate
        with pytest.raises(ValidationError):
            SignalAlertCreate(
                trigger_time=datetime.now(timezone.utc),
                total_score=-1.0,
                alert_level="LEVEL_1",
            )

    def test_hawkes_branching_ratio_bounds(self):
        from backend.models.signal import SignalAlertCreate
        with pytest.raises(ValidationError):
            SignalAlertCreate(
                trigger_time=datetime.now(timezone.utc),
                total_score=2.0,
                alert_level="LEVEL_1",
                hawkes_branching_ratio=1.5,  # > 1
            )

    def test_full_alert_with_id(self):
        from backend.models.signal import SignalAlert
        s = SignalAlert(
            id=1,
            trigger_time=datetime.now(timezone.utc),
            total_score=2.5,
            alert_level="LEVEL_1",
        )
        assert s.id == 1


# ===========================================================================
# System models
# ===========================================================================

class TestSystemConfigModel:
    def test_create(self):
        from backend.models.system import SystemConfigCreate
        sc = SystemConfigCreate(key="alpha_factor", value="1.0")
        assert sc.description is None

    def test_full_config(self):
        from backend.models.system import SystemConfig
        sc = SystemConfig(
            key="test",
            value="42",
            description="Test config",
        )
        assert sc.updated_at is None


class TestValidationAuditModel:
    def test_create(self):
        from backend.models.system import ValidationAudit
        va = ValidationAudit(
            id=1,
            timestamp=datetime.now(timezone.utc),
            source="gexmetrix",
            check_type="range",
            check_name="net_gex_positive",
            passed=True,
        )
        assert va.severity == "INFO"
        assert va.retry_count == 0


class TestGatewaySnapshotModel:
    def test_create(self):
        from backend.models.system import GatewaySnapshot
        gs = GatewaySnapshot(
            id=1,
            timestamp=datetime.now(timezone.utc),
            source="pipeline",
        )
        assert gs.status == "OK"
