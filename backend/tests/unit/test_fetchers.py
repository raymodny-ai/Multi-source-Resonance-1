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
        """GEXMetrix always tries the live API path (FIX-11 site-level key).

        ``GEXMetrixFetcher._mock_mode_key`` deliberately returns ``"none"`` —
        a key NOT present in ``Settings.is_mock_mode``'s key_map. This means
        ``is_mock_mode()`` short-circuits to ``False`` so the fetcher always
        hits the live URL (the public site-level X-API-Key is bundled in the
        GEXMetrix dashboard JS). Mock data is only returned on actual fetch
        failure — see ``test_retry_falls_back_to_mock_on_failure``.
        """
        from backend.fetchers.gexmetrix_fetcher import GEXMetrixFetcher

        config = _make_settings()
        fetcher = GEXMetrixFetcher(config)
        # FIX-11: site-level API key means GEXMetrix never enters mock mode
        # purely because ``gexmetrix_api_key`` is unset.
        assert fetcher._is_mock_mode() is False
        # But the mock data path itself is still wired up for fallback.
        assert isinstance(fetcher._mock_data(), dict)

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
# Crypto Fetcher (migrated to base.py)
# ===========================================================================

class TestCryptoFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.crypto_fetcher import CryptoFetcher

        config = _make_settings()
        fetcher = CryptoFetcher(config)
        data = fetcher._generate_mock_data()
        assert "btc_funding_rate" in data
        assert "btc_oi" in data
        assert "timestamp" in data
        assert isinstance(data["btc_funding_rate"], float)

    @pytest.mark.asyncio
    async def test_fetch_returns_result(self):
        """Hyperliquid live output never fabricates unavailable OI signals.

        2026-08-02: updated for the metaAndAssetCtxs shape (openInterest,
        funding, markPx in the per-asset context) that replaced the old
        meta endpoint + ozSum (which was always null).
        """
        from backend.fetchers.crypto_fetcher import CryptoFetcher

        config = _make_settings()
        fetcher = CryptoFetcher(config)
        fetcher._post_json = AsyncMock(side_effect=[
            [  # metaAndAssetCtxs -> [universe, asset_ctxs]
                {"universe": [{"name": "BTC"}]},
                [{"openInterest": "25000", "markPx": "60000", "funding": "0.002"}],
            ],
        ])
        fetcher._fetch_coingecko = AsyncMock(return_value={
            "btc_price": 60000.0,
            "btc_24h_change": -1.0,
            "btc_volume": 1.2e10,
        })

        result = await fetcher.fetch()
        assert result["btc_funding_rate"] == 0.002
        assert result["btc_oi"] == 25000.0
        # ELR proxy = (oi * mark) / (volume/24) = (25000*60000) / (1.2e10/24)
        assert result["cryptoquant_elr"] is not None
        assert result["oi_change_1h"] is None  # computed by DataWriter
        assert result["oi_crash"] is False
        assert result["liquidation_spike"] is False
        assert result["leverage_cleanup"] is True


# ===========================================================================
# Darkpool Fetcher
# ===========================================================================

class TestDarkpoolFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        """Mock remains synthetic while the SqueezeMetrics path stays factual."""
        from backend.fetchers.darkpool_fetcher import DarkpoolFetcher

        config = _make_settings()
        fetcher = DarkpoolFetcher(config)
        data = fetcher._generate_mock_data()
        assert "dix_value" in data
        assert "date" in data
        assert "aggregated_signal" in data
        assert isinstance(data["dix_value"], float)

        response = MagicMock()
        response.text = "date,price,dix,gex\n2026-07-30,6300,0.44,1.0\n2026-07-31,6350,0.46,1.2"
        response.raise_for_status.return_value = None
        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        fetcher._get_client = AsyncMock(return_value=client)

        live = await fetcher._fetch_squeezemetrics()
        assert live["dix_value"] == 46.0
        # Short Ratio has no free source — stays None (needs paid key).
        assert live["chartexchange_short_ratio"] is None
        # Slopes need >=3 price points; the 2-row fixture yields None.
        assert live["stockgrid_20d_slope"] is None
        assert live["stockgrid_60d_slope"] is None
        # 2026-08-02: v_net/EMA/zero-cross are now computed from the real DIX
        # series (DIX 46 -> v_net = (46-50)*20 = -80), not hardcoded None.
        assert live["v_net"] == -80.0
        assert live["ema_fast_5"] is not None
        assert live["ema_slow_20"] is not None
        assert live["zero_cross_signal"] in ("bullish_cross", "bearish_cross")
        assert live["momentum_reversal_signal"] is None or live["momentum_reversal_signal"].startswith("reversal")


# ===========================================================================
# Flow Fetcher
# ===========================================================================

class TestFlowFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.flow_fetcher import FlowFetcher

        config = _make_settings()
        fetcher = FlowFetcher(config)
        result = await fetcher.fetch()
        assert "net_money_flow" in result
        assert "institutional_flow" in result
        assert "flow_direction" in result


# ===========================================================================
# Sentiment Fetcher
# ===========================================================================

class TestSentimentFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.sentiment_fetcher import SentimentFetcher

        config = _make_settings()
        fetcher = SentimentFetcher(config)
        result = await fetcher.fetch()
        assert "fear_greed_index" in result
        assert "fear_greed_label" in result
        assert "aaii_bull_pct" in result


# ===========================================================================
# Macro Fetcher
# ===========================================================================

class TestMacroFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.macro_fetcher import MacroFetcher

        config = _make_settings()
        fetcher = MacroFetcher(config)
        result = await fetcher.fetch()
        assert "treasury_2y" in result
        assert "treasury_10y" in result
        assert "yield_curve_slope" in result
        assert "fed_funds_rate" in result


# ===========================================================================
# Sector Fetcher
# ===========================================================================

class TestSectorFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.sector_fetcher import SectorFetcher

        config = _make_settings()
        fetcher = SectorFetcher(config)
        result = await fetcher.fetch()
        assert "sector_performance" in result
        assert "rotation_signal" in result
        assert "best_sector" in result
        assert result["rotation_signal"] in ("risk_on", "risk_off", "neutral")


# ===========================================================================
# Put/Call Fetcher
# ===========================================================================

class TestPutCallFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.put_call_fetcher import PutCallFetcher

        config = _make_settings()
        fetcher = PutCallFetcher(config)
        result = await fetcher.fetch()
        assert "equity_put_call_ratio" in result
        assert "index_put_call_ratio" in result
        assert "total_put_call_ratio" in result
        assert "pcr_signal" in result


# ===========================================================================
# VIX Term Structure Fetcher
# ===========================================================================

class TestVIXTermFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.vix_term_fetcher import VIXTermFetcher

        config = _make_settings()
        fetcher = VIXTermFetcher(config)
        result = await fetcher.fetch()
        assert "vix_spot" in result
        assert "vx1" in result
        assert "vx2" in result
        assert "term_structure_state" in result


# ===========================================================================
# LLM Fetcher
# ===========================================================================

class TestLLMFetcher:

    @pytest.mark.asyncio
    async def test_mock_data_structure(self):
        from backend.fetchers.llm_fetcher import LLMFetcher

        config = _make_settings()
        fetcher = LLMFetcher(config)
        result = await fetcher.fetch()
        assert "analysis" in result
        assert "signal" in result
        assert "confidence" in result
        assert result["signal"] in ("bullish", "bearish", "neutral")
