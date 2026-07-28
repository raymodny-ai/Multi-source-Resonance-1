"""
Backtest engine — compatibility layer.

This module re-exports from the new backend/backtest_engine/ package.
All core logic has been moved to the modular package structure:

    backend/backtest_engine/
    ├── __init__.py
    ├── engine.py          — Core BacktestEngine
    ├── metrics.py         — Performance metrics (Sharpe, Sortino, Calmar, MaxDD)
    ├── walk_forward.py    — Walk-forward validation
    ├── sensitivity.py     — Parameter sensitivity analysis
    └── visualizer.py      — Visualization data generation

Import from backend.backtest_engine for the full modular API.
This file is kept for backward compatibility.
"""

# Re-export all public symbols from the new package
from backend.backtest_engine.engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    TradeRecord,
)
from backend.backtest_engine.metrics import (
    PerformanceMetrics,
    calculate_metrics,
)
from backend.backtest_engine.walk_forward import (
    WalkForwardResult,
    run_walk_forward,
)
from backend.backtest_engine.sensitivity import (
    SensitivityResult,
    run_sensitivity,
)
from backend.backtest_engine.visualizer import (
    EquityCurveData,
    TradeDistribution,
    WalkForwardComparison,
    build_equity_curve_data,
    build_trade_distribution,
    build_walk_forward_comparison,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "TradeRecord",
    "PerformanceMetrics",
    "calculate_metrics",
    "WalkForwardResult",
    "run_walk_forward",
    "SensitivityResult",
    "run_sensitivity",
    "EquityCurveData",
    "TradeDistribution",
    "WalkForwardComparison",
    "build_equity_curve_data",
    "build_trade_distribution",
    "build_walk_forward_comparison",
]
