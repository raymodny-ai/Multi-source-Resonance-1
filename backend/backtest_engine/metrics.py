"""
Backtest performance metrics calculation.

Computes Sharpe, Sortino, Calmar, Max Drawdown, Win Rate,
Profit Factor, and other standard performance indicators.
"""

import numpy as np
from typing import Any
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Computed performance metrics for a backtest."""

    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    avg_holding_days: float = 0.0
    information_ratio: float = 0.0


def calculate_metrics(
    trades: list[dict],
    equity_curve: list[float],
    risk_free_rate: float = 0.04,
) -> PerformanceMetrics:
    """Calculate comprehensive performance metrics from trades and equity curve.

    Args:
        trades: List of trade dicts with 'pnl', 'pnl_pct', 'holding_days' keys.
        equity_curve: List of equity values over time.
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculation.

    Returns:
        PerformanceMetrics with all computed indicators.
    """
    if not trades:
        return PerformanceMetrics()

    pnl_pcts = np.array([t.get("pnl_pct", 0) for t in trades], dtype=float)
    equities = np.array(equity_curve, dtype=float)

    # Returns
    total_return_pct = ((equities[-1] / equities[0]) - 1.0) * 100.0
    n_days = max(1, len(trades))
    annualized_return_pct = ((1.0 + total_return_pct / 100.0) ** (252.0 / n_days) - 1.0) * 100.0

    # Daily returns for ratio calculations
    daily_returns = np.diff(equities) / equities[:-1]
    if len(daily_returns) == 0:
        daily_returns = np.array([0.0])

    # Sharpe Ratio
    excess_returns = daily_returns - risk_free_rate / 252.0
    sharpe = 0.0
    if np.std(excess_returns) > 1e-10:
        sharpe = float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

    # Sortino Ratio (downside deviation only)
    downside = daily_returns[daily_returns < 0]
    sortino = 0.0
    if len(downside) > 0 and np.std(downside) > 1e-10:
        sortino = float(np.mean(excess_returns) / np.std(downside) * np.sqrt(252))

    # Max Drawdown
    running_max = np.maximum.accumulate(equities)
    drawdowns = (equities - running_max) / running_max
    max_dd_pct = float(np.min(drawdowns)) * 100.0

    # Max drawdown duration
    max_dd_duration = _max_drawdown_duration(equities)

    # Calmar Ratio
    calmar = 0.0
    if abs(max_dd_pct) > 1e-10:
        calmar = annualized_return_pct / abs(max_dd_pct)

    # Win/Loss stats
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) <= 0]
    win_rate = len(winning) / len(trades) * 100.0 if trades else 0.0

    avg_win = np.mean([t.get("pnl_pct", 0) for t in winning]) if winning else 0.0
    avg_loss = abs(np.mean([t.get("pnl_pct", 0) for t in losing])) if losing else 1.0
    gross_profit = sum(t.get("pnl", 0) for t in winning) if winning else 0.0
    gross_loss = abs(sum(t.get("pnl", 0) for t in losing)) if losing else 1.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    avg_holding = np.mean([t.get("holding_days", 0) for t in trades])

    # Information Ratio (vs benchmark = 0)
    tracking_error = np.std(daily_returns)
    info_ratio = 0.0
    if tracking_error > 1e-10:
        info_ratio = float(np.mean(daily_returns) / tracking_error * np.sqrt(252))

    return PerformanceMetrics(
        total_return_pct=round(total_return_pct, 2),
        annualized_return_pct=round(annualized_return_pct, 2),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        max_drawdown_pct=round(max_dd_pct, 2),
        max_drawdown_duration_days=max_dd_duration,
        win_rate_pct=round(win_rate, 2),
        profit_factor=round(profit_factor, 4),
        total_trades=len(trades),
        winning_trades=len(winning),
        losing_trades=len(losing),
        avg_win_pct=round(float(avg_win), 4),
        avg_loss_pct=round(float(avg_loss), 4),
        avg_holding_days=round(float(avg_holding), 1),
        information_ratio=round(info_ratio, 4),
    )


def _max_drawdown_duration(equities: np.ndarray) -> int:
    """Calculate the longest drawdown period in days."""
    if len(equities) < 2:
        return 0

    running_max = np.maximum.accumulate(equities)
    in_drawdown = equities < running_max
    max_duration = 0
    current_duration = 0

    for dd in in_drawdown:
        if dd:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    return max_duration
