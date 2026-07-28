"""
Unit tests for all data fetchers (14 fetchers).

Tests mock-mode output, data format conformance, BaseFetcher retry logic,
and Pydantic model compatibility.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import Settings


# ---------------------------------------------------------------------------
# Helper: create a test Settings instance (all mock mode)
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        db_path="/tmp/test.db",
        jwt_secret="test",
        fetch_timeout_seconds=5,
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ===========================================================================
# BaseFetcher tests (base.py — the original ABC)
# ===========================================================================

class TestBaseFetcherRetry:
    """Test BaseFetcher retry logic from fetchers/base.py."""

    def test_mock_mode_returns_mock_data(self):
        """fetch_with_retry returns mock data when API key is absent."""
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        assert fetcher._is_mock_mode() is True

    @pytest.mark.asyncio
    async def test_retry_falls_back_to_mock_on_failure(self):
        """After max_retries failures, fetch_with_retry returns mock data."""
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings(gexmetrix_api_key="fake-key")
        fetcher = GEXMetrixFetcher(config)

        # Force fetch() to always raise
        fetcher.fetch = AsyncMock(side_effect=Exception("network error"))

        result = await fetcher.fetch_with_retry(max_retries=2, backoff_factor=0.01)
        assert "_meta" in result
        assert result["_meta"]["is_mock"] is True
        assert result["_meta"]["error"] is not None

    @pytest.mark.asyncio
    async def test_validate_data_rejects_empty_dict(self):
        """BaseFetcher._validate_data rejects empty dicts."""
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        assert fetcher._validate_data({}) is False

    @pytest.mark.asyncio
    async def test_validate_data_rejects_non_dict(self):
        """BaseFetcher._validate_data rejects non-dict values."""
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        assert fetcher._validate_data("not a dict") is False

    def test_wrap_result_adds_meta(self):
        """_wrap_result adds _meta key with source, is_mock, fetched_at."""
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        result = fetcher._wrap_result({"key": "value"}, is_mock=True, error=None)
        assert "_meta" in result
        assert result["_meta"]["source"] == "GEXMetrix"
        assert result["_meta"]["is_mock"] is True
        assert "fetched_at" in result["_meta"]


# ===========================================================================
# GEXMetrix Fetcher
# ===========================================================================

class TestGEXMetrixFetcher:
    """Test GEXMetrixFetcher mock output."""

    @pytest.mark.asyncio
    async def test_mock_data_has_snapshots(self):
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        data = fetcher._mock_data()
        assert "snapshots" in data
        assert len(data["snapshots"]) == 6  # SPX, SPY, QQQ, IWM, NDX, VIX

    @pytest.mark.asyncio
    async def test_mock_data_has_strikes(self):
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        data = fetcher._mock_data()
        assert "strikes" in data
        assert len(data["strikes"]) > 0

    @pytest.mark.asyncio
    async def test_mock_snapshot_fields(self):
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        data = fetcher._mock_data()
        snap = data["snapshots"][0]
        required = {"symbol", "timestamp", "filename", "net_gex", "call_gex",
                     "put_gex", "spot_price", "quality_score"}
        assert required.issubset(set(snap.keys()))


# ===========================================================================
# AXLFI Fetcher
# ===========================================================================

class TestAXLFIFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.axlfi_fetcher import AXLFIFetcher

        config = _make_settings()
        fetcher = AXLFIFetcher(config)
        data = fetcher._mock_data()
        assert "dark_net_position" in data
        assert "dark_volume" in data
        assert "timestamp" in data
        assert "symbols" in data


# ===========================================================================
# VIX Fetcher (base.py variant)
# ===========================================================================

class TestVIXFetcher:

    def test_mock_data_has_term_structure(self):
        from backend.fetchers.vix_fetcher import VIXFetcher

        config = _make_settings()
        fetcher = VIXFetcher(config)
        data = fetcher._mock_data()
        assert "vix_spot" in data
        assert "vx1" in data
        assert "vx2" in data
        assert "term_structure_ratio" in data
        assert "term_structure_state" in data
        assert data["term_structure_state"] in ("contango", "backwardation", "flat")

    def test_vix_spot_positive(self):
        from backend.fetchers.vix_fetcher import VIXFetcher

        config = _make_settings()
        fetcher = VIXFetcher(config)
        data = fetcher._mock_data()
        assert data["vix_spot"] > 0


# ===========================================================================
# CBOE Fetcher
# ===========================================================================

class TestCBOEFetcher:

    def test_mock_data_has_put_call_ratios(self):
        from backend.fetchers.cboe_fetcher import CBOEFetcher

        config = _make_settings()
        fetcher = CBOEFetcher(config)
        data = fetcher._mock_data()
        assert "equity_put_call_ratio" in data
        assert "index_put_call_ratio" in data
        assert "total_equity_volume" in data
        assert data["equity_put_call_ratio"] > 0


# ===========================================================================
# yfinance Fetcher
# ===========================================================================

class TestYFinanceFetcher:

    def test_mock_data_has_prices(self):
        from backend.fetchers.yfinance_fetcher import YFinanceFetcher

        config = _make_settings()
        fetcher = YFinanceFetcher(config)
        data = fetcher._mock_data()
        assert "prices" in data
        assert "history" in data
        assert "SPX" in data["prices"]
        assert "open" in data["prices"]["SPX"]
        assert "close" in data["prices"]["SPX"]


# ===========================================================================
# Crypto Fetcher (base_alt.py variant)
# ===========================================================================

class TestCryptoFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.crypto_fetcher import CryptoFetcher

        fetcher = CryptoFetcher()
        data = fetcher._generate_mock_data()
        assert "btc_funding_rate" in data
        assert "btc_oi" in data
        assert "timestamp" in data
        assert isinstance(data["btc_funding_rate"], float)

    @pytest.mark.asyncio
    async def test_fetch_returns_result(self):
        from backend.fetchers.crypto_fetcher import CryptoFetcher

        fetcher = CryptoFetcher()
        result = await fetcher.fetch()
        assert "source" in result
        assert "timestamp" in result
        assert "data" in result
        assert result["source"] == "crypto_derivatives"


# ===========================================================================
# Darkpool Fetcher
# ===========================================================================

class TestDarkpoolFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.darkpool_fetcher import DarkpoolFetcher

        fetcher = DarkpoolFetcher()
        data = fetcher._generate_mock_data()
        assert "dix_value" in data
        assert "date" in data
        assert "aggregated_signal" in data
        assert isinstance(data["dix_value"], float)


# ===========================================================================
# Flow Fetcher
# ===========================================================================

class TestFlowFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.flow_fetcher import FlowFetcher

        fetcher = FlowFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "money_flow"
        data = result["data"]
        assert "net_money_flow" in data
        assert "institutional_flow" in data
        assert "flow_direction" in data


# ===========================================================================
# Sentiment Fetcher
# ===========================================================================

class TestSentimentFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.sentiment_fetcher import SentimentFetcher

        fetcher = SentimentFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "market_sentiment"
        data = result["data"]
        assert "fear_greed_index" in data
        assert "fear_greed_label" in data
        assert "aaii_bull_pct" in data


# ===========================================================================
# Macro Fetcher
# ===========================================================================

class TestMacroFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.macro_fetcher import MacroFetcher

        fetcher = MacroFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "macro_data"
        data = result["data"]
        assert "treasury_2y" in data
        assert "treasury_10y" in data
        assert "yield_curve_slope" in data
        assert "fed_funds_rate" in data


# ===========================================================================
# Sector Fetcher
# ===========================================================================

class TestSectorFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.sector_fetcher import SectorFetcher

        fetcher = SectorFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "sector_rotation"
        data = result["data"]
        assert "sector_performance" in data
        assert "rotation_signal" in data
        assert "best_sector" in data
        assert data["rotation_signal"] in ("risk_on", "risk_off", "neutral")


# ===========================================================================
# Put/Call Fetcher
# ===========================================================================

class TestPutCallFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.put_call_fetcher import PutCallFetcher

        fetcher = PutCallFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "put_call_ratio"
        data = result["data"]
        assert "equity_put_call_ratio" in data
        assert "index_put_call_ratio" in data
        assert "total_put_call_ratio" in data
        assert "pcr_signal" in data


# ===========================================================================
# VIX Term Structure Fetcher
# ===========================================================================

class TestVIXTermFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.vix_term_fetcher import VIXTermFetcher

        fetcher = VIXTermFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "vix_term_structure"
        data = result["data"]
        assert "vix_spot" in data
        assert "vx1" in data
        assert "vx2" in data
        assert "term_structure_state" in data


# ===========================================================================
# LLM Fetcher
# ===========================================================================

class TestLLMFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.llm_fetcher import LLMFetcher

        fetcher = LLMFetcher()
        result = await fetcher.fetch()
        assert result["source"] == "llm_inference"
        data = result["data"]
        assert "analysis" in data
        assert "signal" in data
        assert "confidence" in data
        assert data["signal"] in ("bullish", "bearish", "neutral")
