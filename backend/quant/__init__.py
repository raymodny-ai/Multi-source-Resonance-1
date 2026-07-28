"""
Quantitative logic layer — multi-source resonance signal engine.

Exports all analyzers, scoring engine, and Hawkes model.
Each analyzer follows the unified interface: async analyze(data: dict) -> dict
"""

from backend.quant.gex_analyzer import analyze as gex_analyze
from backend.quant.vix_analyzer import analyze as vix_analyze
from backend.quant.crypto_analyzer import analyze as crypto_analyze
from backend.quant.darkpool_analyzer import analyze as darkpool_analyze
from backend.quant.flow_analyzer import analyze as flow_analyze
from backend.quant.sentiment_analyzer import analyze as sentiment_analyze
from backend.quant.put_call_analyzer import analyze as put_call_analyze
from backend.quant.vix_term_analyzer import analyze as vix_term_analyze
from backend.quant.sector_analyzer import analyze as sector_analyze
from backend.quant.macro_analyzer import analyze as macro_analyze
from backend.quant.llm_analyzer import analyze as llm_analyze

from backend.quant.scoring import (
    calculate_score,
    calculate_score_from_analyses,
    determine_level,
    get_dimension_summary,
    WEIGHTS,
    RAW_MAX,
    LEVEL_THRESHOLDS,
)

from backend.quant.hawkes_model import (
    HawkesAR1Model,
    analyze as hawkes_analyze,
)

from backend.quant.backtest_engine import (
    BacktestEngine,
    BacktestResult,
    BacktestConfig,
    PerformanceMetrics,
)

from backend.quant.bayesian_weights import (
    BayesianWeightAdapter,
    get_adapted_weights,
    calculate_score_with_bayesian_weights,
)

from backend.quant.llm_cache import (
    LLMCache,
    cached_llm_analyze,
    get_cache,
)

__all__ = [
    # Core analyzers
    "gex_analyze",
    "vix_analyze",
    "crypto_analyze",
    "darkpool_analyze",
    "flow_analyze",
    "sentiment_analyze",
    "put_call_analyze",
    "vix_term_analyze",
    "sector_analyze",
    "macro_analyze",
    "llm_analyze",
    # Scoring engine
    "calculate_score",
    "calculate_score_from_analyses",
    "determine_level",
    "get_dimension_summary",
    "WEIGHTS",
    "RAW_MAX",
    "LEVEL_THRESHOLDS",
    # Hawkes model
    "HawkesAR1Model",
    "hawkes_analyze",
    # Backtest engine
    "BacktestEngine",
    "BacktestResult",
    "BacktestConfig",
    "PerformanceMetrics",
    # Bayesian weights
    "BayesianWeightAdapter",
    "get_adapted_weights",
    "calculate_score_with_bayesian_weights",
    # LLM cache
    "LLMCache",
    "cached_llm_analyze",
    "get_cache",
]
