"""
Parameter sensitivity analysis for backtest engine.

Analyzes how sensitive performance metrics (especially Sharpe ratio)
are to changes in each dimension's weight. Varies each weight ±50%
from default while keeping others fixed.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default raw max for normalization
RAW_MAX = 5.0


class SensitivityResult(BaseModel):
    """Parameter sensitivity analysis result for one dimension."""

    parameter_name: str
    values_tested: list[float]
    sharpe_per_value: list[float]
    return_per_value: list[float]
    optimal_value: float = 0.0
    optimal_sharpe: float = 0.0


def run_sensitivity(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    base_weights: dict[str, float],
    config: dict[str, Any],
    trade_generator: Any,
    initial_capital: float = 100000.0,
) -> list[SensitivityResult]:
    """Analyze how sensitive Sharpe ratio is to each dimension's weight.

    Varies each weight ±50% from default while keeping others fixed.
    Total weight is renormalized after each change.

    Args:
        signals_df: Historical signal data.
        prices_df: Historical price data.
        base_weights: Default dimension weights.
        config: Backtest configuration dict.
        trade_generator: Callable that generates trades from signals.
        initial_capital: Starting capital.

    Returns:
        List of SensitivityResult, one per dimension weight.
    """
    results: list[SensitivityResult] = []

    for dim_name, base_value in base_weights.items():
        values_tested: list[float] = []
        sharpes: list[float] = []
        returns: list[float] = []

        # Test 5 points: -50%, -25%, base, +25%, +50%
        multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]

        for mult in multipliers:
            test_weights = dict(base_weights)
            test_weights[dim_name] = round(base_value * mult, 4)

            # Renormalize to keep total constant
            total = sum(test_weights.values())
            test_weights = {k: v * (RAW_MAX / total) for k, v in test_weights.items()}

            trades = trade_generator(signals_df, prices_df, test_weights, config)

            if not trades:
                values_tested.append(test_weights[dim_name])
                sharpes.append(0.0)
                returns.append(0.0)
                continue

            equity = [initial_capital]
            for t in trades:
                pnl = t.get("pnl", 0) if isinstance(t, dict) else getattr(t, "pnl", 0)
                equity.append(equity[-1] + pnl)

            equity_arr = np.array(equity, dtype=float)
            ret = (
                np.diff(equity_arr) / equity_arr[:-1]
                if len(equity_arr) > 1
                else np.array([0.0])
            )

            sharpe = 0.0
            if np.std(ret) > 1e-10:
                sharpe = float(np.mean(ret) / np.std(ret) * np.sqrt(252))

            total_ret = ((equity_arr[-1] / equity_arr[0]) - 1.0) * 100.0

            values_tested.append(round(test_weights[dim_name], 4))
            sharpes.append(round(sharpe, 4))
            returns.append(round(total_ret, 2))

        # Find optimal
        if sharpes:
            best_idx = int(np.argmax(sharpes))
            optimal_value = values_tested[best_idx]
            optimal_sharpe = sharpes[best_idx]
        else:
            optimal_value = base_value
            optimal_sharpe = 0.0

        results.append(SensitivityResult(
            parameter_name=f"weight_{dim_name}",
            values_tested=values_tested,
            sharpe_per_value=sharpes,
            return_per_value=returns,
            optimal_value=optimal_value,
            optimal_sharpe=optimal_sharpe,
        ))

    return results
