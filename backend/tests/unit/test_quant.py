"""
Unit tests for the quantitative analysis modules:
- Each analyzer's analyze() method (gex, vix, crypto, darkpool)
- scoring.py: score calculation, normalization, level determination
- hawkes_model.py: AR(1) fitting, prediction, regime classification
- Edge cases: empty data, extreme values
"""

import copy

import numpy as np
import pytest

from backend.quant import scoring
from backend.quant.hawkes_model import HawkesAR1Model, analyze as hawkes_analyze


@pytest.fixture(autouse=True)
def _reset_bayesian_weights():
    """Ensure each test starts with default weights (no Bayesian adaptation)."""
    scoring.reset_weights()
    # Also reset the module-level adapter so get_current_weights returns defaults
    scoring._adapter_instance = None
    yield
    scoring._adapter_instance = None


# ===========================================================================
# GEX Analyzer
# ===========================================================================

class TestGEXAnalyzer:

    @pytest.mark.asyncio
    async def test_analyze_with_positive_net_gex(self):
        from backend.quant.gex_analyzer import analyze

        data = {
            "net_gex": 500_000_000,
            "call_gex": 1_200_000_000,
            "put_gex": -700_000_000,
            "call_wall": 5800.0,
            "put_wall": 5600.0,
            "zero_gamma_level": 5700.0,
            "spot_price": 5750.0,
            "total_gamma": 1_900_000_000,
        }
        result = await analyze(data)
        assert "score" in result
        assert "level" in result
        assert "signals" in result
        assert "details" in result
        assert result["score"] >= 0
        assert "net_gex_positive" in result["signals"]

    @pytest.mark.asyncio
    async def test_analyze_empty_data_returns_default(self):
        from backend.quant.gex_analyzer import analyze

        result = await analyze(None)
        assert result["score"] == 0.0
        assert result["level"] == "LEVEL_0"

    @pytest.mark.asyncio
    async def test_analyze_empty_dict(self):
        from backend.quant.gex_analyzer import analyze

        result = await analyze({})
        assert result["score"] == 0.0
        assert result["level"] == "LEVEL_0"

    @pytest.mark.asyncio
    async def test_analyze_negative_gex_regime(self):
        from backend.quant.gex_analyzer import analyze

        data = {
            "net_gex": -1_000_000_000,
            "call_gex": 500_000_000,
            "put_gex": -1_500_000_000,
            "spot_price": 5750.0,
            "total_gamma": 2_000_000_000,
        }
        result = await analyze(data)
        assert result["details"]["gex_regime"] == "negative"

    @pytest.mark.asyncio
    async def test_score_bounded_0_100(self):
        from backend.quant.gex_analyzer import analyze

        # Extreme values
        data = {
            "net_gex": 1e15,
            "call_gex": 1e15,
            "put_gex": 0,
            "call_wall": 99999,
            "put_wall": 1,
            "zero_gamma_level": 5000,
            "spot_price": 5000,
            "total_gamma": 1e15,
        }
        result = await analyze(data)
        assert 0 <= result["score"] <= 100


# ===========================================================================
# VIX Analyzer
# ===========================================================================

class TestVIXAnalyzer:

    @pytest.mark.asyncio
    async def test_analyze_contango(self):
        from backend.quant.vix_analyzer import analyze

        data = {
            "vix_spot": 15.0,
            "vx1": 16.0,
            "vx2": 17.0,
            "term_structure_ratio": 0.0625,
            "term_structure_state": "contango",
            "panic_premium": -1.0,
        }
        result = await analyze(data)
        assert result["score"] > 0
        # 2026-08-02 (方案 A): ratio 0.0625 → 'term_structure_normalizing'
        assert "term_structure_normalizing" in result["signals"]

    @pytest.mark.asyncio
    async def test_analyze_empty_data(self):
        from backend.quant.vix_analyzer import analyze

        result = await analyze(None)
        assert result["score"] == 0.0
        assert result["level"] == "LEVEL_0"

    @pytest.mark.asyncio
    async def test_analyze_extreme_vix(self):
        from backend.quant.vix_analyzer import analyze

        data = {
            "vix_spot": 45.0,
            "vx1": 30.0,
            "vx2": 28.0,
            "term_structure_ratio": -0.067,
            "term_structure_state": "backwardation",
            "panic_premium": 15.0,
        }
        result = await analyze(data)
        assert "vix_extreme_contrarian" in result["signals"]
        assert 0 <= result["score"] <= 100


# ===========================================================================
# Crypto Analyzer
# ===========================================================================

class TestCryptoAnalyzer:

    @pytest.mark.asyncio
    async def test_analyze_leverage_cleanup(self):
        from backend.quant.crypto_analyzer import analyze

        data = {
            "btc_funding_rate": -0.002,
            "btc_oi": 22000.0,
            "oi_change_1h": -0.15,
            "liquidation_spike": True,
            "leverage_cleanup": True,
            "funding_anomaly": True,
            "oi_crash": True,
            "cryptoquant_elr": 1.2,
        }
        result = await analyze(data)
        assert result["score"] > 0
        assert "leverage_cleanup" in result["signals"]
        assert "oi_crash" in result["signals"]

    @pytest.mark.asyncio
    async def test_analyze_empty_data(self):
        from backend.quant.crypto_analyzer import analyze

        result = await analyze(None)
        assert result["score"] == 0.0
        assert result["details"]["sentiment"] == "neutral"

    @pytest.mark.asyncio
    async def test_sentiment_extreme_fear(self):
        from backend.quant.crypto_analyzer import analyze

        data = {
            "btc_funding_rate": -0.005,
            "leverage_cleanup": True,
            "oi_crash": True,
            "liquidation_spike": True,
            "funding_anomaly": True,
        }
        result = await analyze(data)
        assert result["details"]["sentiment"] in ("extreme_fear_cleanup", "fear")


# ===========================================================================
# Darkpool Analyzer
# ===========================================================================

class TestDarkpoolAnalyzer:

    @pytest.mark.asyncio
    async def test_analyze_bullish_dix(self):
        from backend.quant.darkpool_analyzer import analyze

        data = {
            "dix_value": 55.0,
            "chartexchange_short_ratio": 4.0,
            "v_net": 200.0,
            "ema_fast_5": 100.0,
            "ema_slow_20": -50.0,
            "zero_cross_signal": "bullish_cross",
            "aggregated_signal": True,
            "dbmf_ma5_recovery": True,
            "stockgrid_divergence": False,
        }
        result = await analyze(data)
        assert result["score"] > 0
        assert "dix_strong_bullish" in result["signals"]
        assert "ema_bullish_cross" in result["signals"]

    @pytest.mark.asyncio
    async def test_analyze_empty_data(self):
        from backend.quant.darkpool_analyzer import analyze

        result = await analyze(None)
        assert result["score"] == 0.0
        assert result["details"]["flow_direction"] == "neutral"

    @pytest.mark.asyncio
    async def test_flow_direction(self):
        from backend.quant.darkpool_analyzer import analyze

        data = {"dix_value": 30.0, "v_net": -500.0}
        result = await analyze(data)
        assert result["details"]["flow_direction"] == "net_short"


# ===========================================================================
# Scoring Engine
# ===========================================================================

class TestScoring:

    def test_calculate_score_all_zero(self):
        result = scoring.calculate_score(0, 0, 0, 0)
        assert result["normalized_score"] == 0.0
        assert result["level"] == "LEVEL_0"

    def test_calculate_score_all_max(self):
        result = scoring.calculate_score(100, 100, 100, 100)
        assert result["normalized_score"] == 100.0
        assert result["level"] == "LEVEL_3"

    def test_calculate_score_partial(self):
        result = scoring.calculate_score(gex_score=50, vix_score=50)
        assert 0 < result["normalized_score"] < 100
        assert result["raw_score"] > 0

    def test_score_clamped(self):
        # Scores > 100 should be clamped
        result = scoring.calculate_score(200, 200, 200, 200)
        assert result["normalized_score"] == 100.0

    def test_negative_scores_clamped(self):
        result = scoring.calculate_score(-50, -50, -50, -50)
        assert result["normalized_score"] == 0.0

    def test_determine_level_boundaries(self):
        assert scoring.determine_level(0) == "LEVEL_0"
        assert scoring.determine_level(24.99) == "LEVEL_0"
        assert scoring.determine_level(25.0) == "LEVEL_1"
        assert scoring.determine_level(50.0) == "LEVEL_2"
        assert scoring.determine_level(75.0) == "LEVEL_3"
        assert scoring.determine_level(100.0) == "LEVEL_3"

    def test_multi_dimension_resonance_bonus(self):
        # 3+ dimensions >= 60 triggers resonance bonus
        result = scoring.calculate_score(80, 80, 80, 0)
        assert "multi_dimension_resonance" in result["signals"]

    def test_dimension_scores_in_result(self):
        result = scoring.calculate_score(30, 40, 50, 60)
        dims = result["dimension_scores"]
        assert dims["gex"] == 30.0
        assert dims["vix"] == 40.0
        assert dims["crypto"] == 50.0
        assert dims["darkpool"] == 60.0

    def test_calculate_score_from_analyses(self):
        gex_r = {"score": 60}
        vix_r = {"score": 40}
        crypto_r = {"score": 50}
        darkpool_r = {"score": 30}
        result = scoring.calculate_score_from_analyses(gex_r, vix_r, crypto_r, darkpool_r)
        assert "normalized_score" in result
        assert result["normalized_score"] > 0

    def test_get_dimension_summary(self):
        result = scoring.calculate_score(50, 50, 50, 50)
        summary = scoring.get_dimension_summary(result)
        assert "level" in summary
        assert "level_description" in summary
        assert "dimensions" in summary

    def test_raw_max_is_8(self):
        assert scoring.RAW_MAX == 8.0

    def test_weights_sum_to_raw_max(self):
        assert sum(scoring.WEIGHTS.values()) == scoring.RAW_MAX

    def test_default_weights_unchanged(self):
        """DEFAULT_WEIGHTS should always match the original hardcoded values."""
        assert scoring.DEFAULT_WEIGHTS == {
            "gex": 2.5,
            "vix": 1.5,
            "crypto": 2.0,
            "darkpool": 2.0,
        }
        assert scoring.WEIGHTS is scoring.DEFAULT_WEIGHTS

    def test_get_current_weights_returns_defaults_initially(self):
        """Before any Bayesian update, weights should equal DEFAULT_WEIGHTS."""
        weights = scoring.get_current_weights()
        assert weights == scoring.DEFAULT_WEIGHTS

    def test_reset_weights_restores_defaults(self):
        """After reset, get_current_weights should return DEFAULT_WEIGHTS."""
        scoring.reset_weights()
        weights = scoring.get_current_weights()
        assert weights == scoring.DEFAULT_WEIGHTS

    def test_calculate_score_with_default_weights(self):
        """Score calculation should use default weights when no Bayesian update."""
        result = scoring.calculate_score(100, 100, 100, 100)
        assert result["normalized_score"] == 100.0
        assert result["dimension_weights"] == scoring.DEFAULT_WEIGHTS


# ===========================================================================
# Bayesian weight persistence (IMPL-BAYESIAN-001 #1)
# ===========================================================================

class TestBayesianPersistence:
    """Serialize/restore round-trip so adapted weights survive restarts."""

    def _make_adapter_with_history(self):
        from backend.quant.bayesian_weights import BayesianWeightAdapter
        a = BayesianWeightAdapter(min_outcomes=1)
        outs = [
            {"gex_score": 80, "vix_score": 50, "crypto_score": 50,
             "darkpool_score": 50, "forward_return": 2.0,
             "trigger_time": "2026-08-01T00:00:00Z", "alert_level": "LEVEL_2"},
            {"gex_score": 60, "vix_score": 50, "crypto_score": 50,
             "darkpool_score": 50, "forward_return": 1.5,
             "trigger_time": "2026-08-02T00:00:00Z", "alert_level": "LEVEL_2"},
        ]
        a.update_weights(outs)
        return a

    def test_serialize_contains_full_state(self):
        a = self._make_adapter_with_history()
        state = a.serialize_state()
        assert set(state) == {
            "posteriors", "priors", "update_count",
            "last_update", "min_outcomes", "decay",
        }
        assert state["update_count"] == 1
        assert set(state["posteriors"]) == {"gex", "vix", "crypto", "darkpool"}

    def test_restore_rehydrates_posteriors_and_weights(self):
        a = self._make_adapter_with_history()
        state = a.serialize_state()
        from backend.quant.bayesian_weights import BayesianWeightAdapter
        b = BayesianWeightAdapter(min_outcomes=1)  # fresh priors
        b.restore_state(state)
        assert b.get_current_weights() == a.get_current_weights()
        assert b.serialize_state()["posteriors"] == state["posteriors"]
        assert b.serialize_state()["update_count"] == state["update_count"]

    def test_restore_graceful_on_bad_input(self):
        from backend.quant.bayesian_weights import BayesianWeightAdapter
        b = BayesianWeightAdapter(min_outcomes=1)
        before = b.serialize_state()
        b.restore_state(None)          # not a dict → no-op
        b.restore_state({})            # empty → no-op
        b.restore_state({"posteriors": {"gex": {"alpha": "bad"}}})  # bad value
        assert b.serialize_state() == before  # unchanged


# ===========================================================================
# Hawkes AR(1) Model
# ===========================================================================

class TestHawkesModel:

    def test_init_defaults(self):
        model = HawkesAR1Model()
        assert model.mu == 0.1
        assert model.alpha == 0.3
        assert model.beta == 1.0

    def test_fit_with_enough_events(self):
        model = HawkesAR1Model()
        events = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        result = model.fit(events)
        assert "branching_ratio" in result
        # Branching ratio is no longer clamped to [0,1] — it may exceed 1 in a
        # supercritical regime. Only the lower bound (no negative self-excitation)
        # is enforced.
        assert result["branching_ratio"] >= 0
        assert result["n_events"] == 10

    def test_fit_too_few_events(self):
        model = HawkesAR1Model()
        events = np.array([1.0, 2.0])
        result = model.fit(events)
        assert result["branching_ratio"] == 0.0

    def test_fit_none_events(self):
        model = HawkesAR1Model()
        result = model.fit(None)
        assert result["n_events"] == 0

    def test_predict_intensity_before_fit(self):
        model = HawkesAR1Model()
        intensities = model.predict_intensity(n_steps=5)
        assert len(intensities) == 5
        assert intensities[0] == model.mu

    def test_predict_intensity_after_fit(self):
        model = HawkesAR1Model()
        events = np.sort(np.random.exponential(scale=1.0, size=50))
        model.fit(events)
        intensities = model.predict_intensity(n_steps=10)
        assert len(intensities) == 10
        assert all(np.isfinite(intensities))

    def test_signal_probability_range(self):
        model = HawkesAR1Model()
        prob = model.signal_probability(current_intensity=1.0)
        assert 0 <= prob <= 1

    def test_signal_probability_zero_intensity(self):
        model = HawkesAR1Model()
        prob = model.signal_probability(current_intensity=0.0)
        assert prob == 0.0

    def test_get_regime_low(self):
        model = HawkesAR1Model()
        model._branching_ratio = 0.1
        assert model.get_regime() == "low"

    def test_get_regime_moderate(self):
        model = HawkesAR1Model()
        model._branching_ratio = 0.35
        assert model.get_regime() == "moderate"

    def test_get_regime_high(self):
        model = HawkesAR1Model()
        model._branching_ratio = 0.7
        assert model.get_regime() == "high"

    def test_get_summary_unfitted(self):
        model = HawkesAR1Model()
        summary = model.get_summary()
        assert summary["branching_ratio"] == 0.0
        assert summary["regime"] == "low"

    def test_get_summary_fitted(self):
        model = HawkesAR1Model()
        events = np.sort(np.random.exponential(scale=1.0, size=30))
        model.fit(events)
        summary = model.get_summary()
        assert "branching_ratio" in summary
        assert "signal_probability" in summary
        assert "regime" in summary
        assert summary["n_events"] > 0

    @pytest.mark.asyncio
    async def test_analyze_function_empty_data(self):
        result = await hawkes_analyze(None)
        assert result["branching_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_function_with_events(self):
        data = {
            "event_times": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "mu": 0.1,
            "alpha": 0.3,
            "beta": 1.0,
        }
        result = await hawkes_analyze(data)
        assert "branching_ratio" in result
        assert "regime" in result
