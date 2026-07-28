"""
Backtest result visualization data generation.

Generates structured data for frontend charts:
- Equity Curve (cumulative portfolio value)
- Drawdown Curve (percentage drawdown from peak)
- Trade distribution histograms
- Walk-forward fold comparison
"""

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EquityCurveData(BaseModel):
    """Equity curve data for charting."""

    timestamps: list[str] = []
    equity_values: list[float] = []
    drawdown_values: list[float] = []
    peak_values: list[float] = []


class TradeDistribution(BaseModel):
    """Trade PnL distribution data."""

    pnl_values: list[float] = []
    pnl_pct_values: list[float] = []
    holding_days: list[int] = []
    win_count: int = 0
    loss_count: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0


class WalkForwardComparison(BaseModel):
    """Walk-forward fold comparison data."""

    fold_indices: list[int] = []
    sharpes: list[float] = []
    returns: list[float] = []
    max_drawdowns: list[float] = []
    trade_counts: list[int] = []


def build_equity_curve_data(
    trades: list[dict],
    equity_curve: list[float],
    timestamps: list[str],
    initial_capital: float = 100000.0,
) -> EquityCurveData:
    """Build equity curve data for frontend visualization.

    Args:
        trades: List of trade dicts.
        equity_curve: List of equity values.
        timestamps: List of timestamp strings.
        initial_capital: Starting capital.

    Returns:
        EquityCurveData with timestamps, equity, drawdown, and peak values.
    """
    if not equity_curve:
        return EquityCurveData()

    equities = np.array(equity_curve, dtype=float)
    running_max = np.maximum.accumulate(equities)
    drawdowns = ((equities - running_max) / running_max) * 100.0

    return EquityCurveData(
        timestamps=timestamps or [str(i) for i in range(len(equities))],
        equity_values=[round(v, 2) for v in equities.tolist()],
        drawdown_values=[round(v, 2) for v in drawdowns.tolist()],
        peak_values=[round(v, 2) for v in running_max.tolist()],
    )


def build_trade_distribution(trades: list[dict]) -> TradeDistribution:
    """Build trade distribution data for histogram visualization.

    Args:
        trades: List of trade dicts with 'pnl', 'pnl_pct', 'holding_days'.

    Returns:
        TradeDistribution with PnL values and summary stats.
    """
    if not trades:
        return TradeDistribution()

    pnl_values = [t.get("pnl", 0) for t in trades]
    pnl_pct_values = [t.get("pnl_pct", 0) for t in trades]
    holding_days = [t.get("holding_days", 0) for t in trades]

    winning = [p for p in pnl_values if p > 0]
    losing = [p for p in pnl_values if p <= 0]

    return TradeDistribution(
        pnl_values=[round(v, 2) for v in pnl_values],
        pnl_pct_values=[round(v, 4) for v in pnl_pct_values],
        holding_days=holding_days,
        win_count=len(winning),
        loss_count=len(losing),
        avg_win=round(float(np.mean(winning)), 2) if winning else 0.0,
        avg_loss=round(float(np.mean(losing)), 2) if losing else 0.0,
    )


def build_walk_forward_comparison(
    walk_forward_results: list[Any],
) -> WalkForwardComparison:
    """Build walk-forward fold comparison data for charting.

    Args:
        walk_forward_results: List of WalkForwardResult objects.

    Returns:
        WalkForwardComparison with per-fold metrics.
    """
    if not walk_forward_results:
        return WalkForwardComparison()

    return WalkForwardComparison(
        fold_indices=[r.fold_index for r in walk_forward_results],
        sharpes=[r.test_sharpe for r in walk_forward_results],
        returns=[r.test_return_pct for r in walk_forward_results],
        max_drawdowns=[r.test_max_dd_pct for r in walk_forward_results],
        trade_counts=[r.test_trades for r in walk_forward_results],
    )
