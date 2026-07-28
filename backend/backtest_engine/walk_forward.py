"""
Walk-forward validation for backtest engine.

Prevents overfitting by splitting data into rolling train/test windows
and evaluating out-of-sample performance across multiple folds.
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WalkForwardResult(BaseModel):
    """Result from a single walk-forward fold."""

    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_sharpe: float = 0.0
    test_return_pct: float = 0.0
    test_max_dd_pct: float = 0.0
    test_trades: int = 0


def run_walk_forward(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    weights: dict[str, float],
    config: dict[str, Any],
    trade_generator: Any,
    initial_capital: float = 100000.0,
) -> list[WalkForwardResult]:
    """Execute walk-forward validation to prevent overfitting.

    Splits data into rolling train/test windows and evaluates
    out-of-sample performance.

    Args:
        signals_df: Historical signal data.
        prices_df: Historical price data.
        weights: Dimension weights for scoring.
        config: Backtest configuration dict.
        trade_generator: Callable that generates trades from signals.
        initial_capital: Starting capital for each fold.

    Returns:
        List of WalkForwardResult, one per fold.
    """
    results: list[WalkForwardResult] = []

    window = config.get("walk_forward_window", 60)
    step = config.get("walk_forward_step", 5)

    if len(signals_df) < window + step:
        logger.warning("Insufficient data for walk-forward validation")
        return results

    n = len(signals_df)
    fold = 0

    for test_start_idx in range(window, n, step):
        train_start_idx = max(0, test_start_idx - window)
        test_end_idx = min(n, test_start_idx + step)

        train_df = signals_df.iloc[train_start_idx:test_start_idx]
        test_df = signals_df.iloc[test_start_idx:test_end_idx]

        if test_df.empty:
            continue

        # Generate trades on test set only
        test_trades = trade_generator(test_df, prices_df, weights, config)

        if not test_trades:
            fold += 1
            continue

        # Calculate test metrics
        equity = [initial_capital]
        for t in test_trades:
            pnl = t.get("pnl", 0) if isinstance(t, dict) else getattr(t, "pnl", 0)
            equity.append(equity[-1] + pnl)

        equity_arr = np.array(equity, dtype=float)
        returns = (
            np.diff(equity_arr) / equity_arr[:-1]
            if len(equity_arr) > 1
            else np.array([0.0])
        )

        test_sharpe = 0.0
        if np.std(returns) > 1e-10:
            test_sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))

        test_return = ((equity_arr[-1] / equity_arr[0]) - 1.0) * 100.0

        running_max = np.maximum.accumulate(equity_arr)
        test_max_dd = float(np.min((equity_arr - running_max) / running_max)) * 100.0

        try:
            train_start_ts = str(train_df.iloc[0].get("trigger_time", ""))
            train_end_ts = str(train_df.iloc[-1].get("trigger_time", ""))
            test_start_ts = str(test_df.iloc[0].get("trigger_time", ""))
            test_end_ts = str(test_df.iloc[-1].get("trigger_time", ""))
        except Exception:
            train_start_ts = train_end_ts = test_start_ts = test_end_ts = ""

        results.append(WalkForwardResult(
            fold_index=fold,
            train_start=train_start_ts,
            train_end=train_end_ts,
            test_start=test_start_ts,
            test_end=test_end_ts,
            test_sharpe=round(test_sharpe, 4),
            test_return_pct=round(test_return, 2),
            test_max_dd_pct=round(test_max_dd, 2),
            test_trades=len(test_trades),
        ))
        fold += 1

    logger.info(f"Walk-forward validation: {len(results)} folds completed")
    return results
