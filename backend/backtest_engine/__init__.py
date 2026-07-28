"""
Backtest engine package — signal performance evaluation with walk-forward validation.

Provides:
- BacktestEngine: Core engine for historical signal replay
- Performance metrics: Sharpe, Sortino, Calmar, MaxDD, WinRate
- Walk-forward validation to prevent overfitting
- Parameter sensitivity analysis
- Visualization data generation (Equity Curve, Drawdown, Trade Distribution)

Usage:
    from backend.backtest_engine import BacktestEngine, BacktestConfig
    engine = BacktestEngine()
    result = await engine.run_backtest(config_dict)
"""

from backend.backtest_engine.engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    TradeRecord,
)
from backend.backtest_engine.metrics import PerformanceMetrics, calculate_metrics
from backend.backtest_engine.walk_forward import WalkForwardResult, run_walk_forward
from backend.backtest_engine.sensitivity import SensitivityResult, run_sensitivity
from backend.backtest_engine.visualizer import (
    EquityCurveData,
    TradeDistribution,
    WalkForwardComparison,
    build_equity_curve_data,
    build_trade_distribution,
    build_walk_forward_comparison,
)

__all__ = [
    # Core engine
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "TradeRecord",
    # Metrics
    "PerformanceMetrics",
    "calculate_metrics",
    # Walk-forward
    "WalkForwardResult",
    "run_walk_forward",
    # Sensitivity
    "SensitivityResult",
    "run_sensitivity",
    # Visualization
    "EquityCurveData",
    "TradeDistribution",
    "WalkForwardComparison",
    "build_equity_curve_data",
    "build_trade_distribution",
    "build_walk_forward_comparison",
]
