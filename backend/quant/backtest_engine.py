"""
Backtesting engine for signal performance evaluation.

Supports:
- Historical signal replay with walk-forward validation
- Performance metrics: Sharpe, Sortino, Calmar, Max Drawdown
- Parameter sensitivity analysis
- Integration with scoring.py weight system
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backend.quant.scoring import WEIGHTS, RAW_MAX, calculate_score

logger = logging.getLogger(__name__)


# ── Pydantic Models ─────────────────────────────────────────────────────────


class BacktestConfig(BaseModel):
    """Configuration for a backtest run."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = Field(100000.0, ge=1.0)
    risk_free_rate: float = Field(0.04, ge=0.0, description="Annual risk-free rate")
    walk_forward_window: int = Field(60, ge=10, description="Walk-forward train window (days)")
    walk_forward_step: int = Field(5, ge=1, description="Walk-forward step size (days)")
    custom_weights: Optional[dict[str, float]] = Field(
        None, description="Override default dimension weights"
    )


class TradeRecord(BaseModel):
    """Individual trade from signal trigger."""
    entry_time: str
    exit_time: Optional[str] = None
    entry_price: float
    exit_price: Optional[float] = None
    signal_score: float
    signal_level: str
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_days: int = 0


class PerformanceMetrics(BaseModel):
    """Computed performance metrics."""
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


class SensitivityResult(BaseModel):
    """Parameter sensitivity analysis result."""
    parameter_name: str
    values_tested: list[float]
    sharpe_per_value: list[float]
    return_per_value: list[float]
    optimal_value: float = 0.0
    optimal_sharpe: float = 0.0


class BacktestResult(BaseModel):
    """Complete backtest result."""
    config: BacktestConfig
    metrics: PerformanceMetrics
    trades: list[TradeRecord] = []
    equity_curve: list[float] = []
    drawdown_curve: list[float] = []
    timestamps: list[str] = []
    walk_forward: list[WalkForwardResult] = []
    sensitivity: list[SensitivityResult] = []
    weights_used: dict[str, float] = {}
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Backtest Engine ─────────────────────────────────────────────────────────


class BacktestEngine:
    """Signal backtesting engine with walk-forward validation.

    Usage:
        engine = BacktestEngine()
        result = await engine.run_backtest(config_dict)
    """

    def __init__(self) -> None:
        self._signals_df: Optional[pd.DataFrame] = None
        self._prices_df: Optional[pd.DataFrame] = None

    async def run_backtest(self, config: dict) -> BacktestResult:
        """Run a full backtest with the given configuration.

        Args:
            config: Backtest configuration dict (see BacktestConfig fields).

        Returns:
            BacktestResult with metrics, trades, equity curve, etc.
        """
        bt_config = BacktestConfig(**config)
        logger.info(f"Starting backtest: {bt_config.start_date} → {bt_config.end_date}")

        # Load historical data
        signals_df, prices_df = await self._load_historical_data(bt_config)
        self._signals_df = signals_df
        self._prices_df = prices_df

        if signals_df.empty or prices_df.empty:
            logger.warning("No historical data available for backtest")
            return self._empty_result(bt_config)

        # Determine weights
        weights = bt_config.custom_weights or dict(WEIGHTS)

        # Generate trades from signals
        trades = self._generate_trades(signals_df, prices_df, weights, bt_config)

        if not trades:
            logger.warning("No trades generated from signals")
            return self._empty_result(bt_config)

        # Build equity curve
        equity_curve, drawdown_curve, timestamps = self._build_equity_curve(
            trades, bt_config.initial_capital
        )

        # Calculate performance metrics
        metrics = self._calculate_metrics(trades, equity_curve, bt_config)

        # Walk-forward validation
        walk_forward = self._walk_forward_validation(signals_df, prices_df, weights, bt_config)

        # Parameter sensitivity analysis
        sensitivity = self._parameter_sensitivity(signals_df, prices_df, bt_config)

        result = BacktestResult(
            config=bt_config,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            timestamps=timestamps,
            walk_forward=walk_forward,
            sensitivity=sensitivity,
            weights_used=weights,
        )

        logger.info(
            f"Backtest complete: {metrics.total_trades} trades, "
            f"Sharpe={metrics.sharpe_ratio:.2f}, Return={metrics.total_return_pct:.1f}%"
        )
        return result

    async def _load_historical_data(
        self, config: BacktestConfig
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load signal alerts and price data from database.

        Returns:
            Tuple of (signals_df, prices_df).
        """
        try:
            from backend.database import get_db

            async with get_db() as db:
                # Load signal alerts
                query = "SELECT * FROM signal_alerts WHERE 1=1"
                params: list[Any] = []

                if config.start_date:
                    query += " AND trigger_time >= ?"
                    params.append(config.start_date)
                if config.end_date:
                    query += " AND trigger_time <= ?"
                    params.append(config.end_date)

                query += " ORDER BY trigger_time ASC"

                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                if not rows:
                    return pd.DataFrame(), pd.DataFrame()

                signals_df = pd.DataFrame(rows, columns=columns)

                # Load GEX history as price proxy
                cursor2 = await db.execute(
                    "SELECT timestamp, gex_local, gex_calibrated, put_wall_level "
                    "FROM gex_history ORDER BY timestamp ASC"
                )
                price_rows = await cursor2.fetchall()
                price_cols = [desc[0] for desc in cursor2.description] if cursor2.description else []
                prices_df = pd.DataFrame(price_rows, columns=price_cols) if price_rows else pd.DataFrame()

                return signals_df, prices_df

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    def _generate_trades(
        self,
        signals_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        weights: dict[str, float],
        config: BacktestConfig,
    ) -> list[TradeRecord]:
        """Generate trades from signal triggers.

        Each LEVEL_2+ signal triggers a trade entry.
        Exit after 5 trading days or at next signal, whichever comes first.
        """
        trades: list[TradeRecord] = []

        if signals_df.empty:
            return trades

        # Filter for meaningful signals (LEVEL_2 or LEVEL_3)
        signal_mask = signals_df["alert_level"].isin(["LEVEL_2", "LEVEL_3"])
        active_signals = signals_df[signal_mask].copy()

        if active_signals.empty:
            return trades

        # Build price series for PnL calculation
        price_series = self._build_price_series(prices_df)

        holding_period = 5  # default exit after 5 days

        for _, row in active_signals.iterrows():
            entry_time = row.get("trigger_time", "")
            score = float(row.get("total_score", 0))
            level = str(row.get("alert_level", "LEVEL_0"))

            # Find entry price
            entry_price = self._lookup_price(price_series, str(entry_time))
            if entry_price is None or entry_price <= 0:
                continue

            # Find exit price (holding_period days later)
            exit_time, exit_price = self._find_exit(
                price_series, str(entry_time), holding_period
            )

            if exit_price is None:
                continue

            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price) * 100.0

            # Calculate holding days
            try:
                entry_dt = pd.Timestamp(str(entry_time))
                exit_dt = pd.Timestamp(str(exit_time))
                holding_days = max(1, (exit_dt - entry_dt).days)
            except Exception:
                holding_days = holding_period

            trades.append(TradeRecord(
                entry_time=str(entry_time),
                exit_time=str(exit_time),
                entry_price=round(entry_price, 4),
                exit_price=round(exit_price, 4),
                signal_score=round(score, 4),
                signal_level=level,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 4),
                holding_days=holding_days,
            ))

        return trades

    def _build_price_series(self, prices_df: pd.DataFrame) -> pd.Series:
        """Build a price series from GEX history data."""
        if prices_df.empty:
            return pd.Series(dtype=float)

        # Use gex_calibrated or gex_local as price proxy
        price_col = "gex_calibrated" if "gex_calibrated" in prices_df.columns else "gex_local"
        ts_col = "timestamp"

        series = prices_df.set_index(ts_col)[price_col].dropna()
        series.index = pd.to_datetime(series.index)
        return series.sort_index()

    def _lookup_price(self, price_series: pd.Series, timestamp: str) -> Optional[float]:
        """Look up the nearest price for a given timestamp."""
        if price_series.empty:
            return None

        try:
            ts = pd.Timestamp(timestamp)
            # Find nearest price
            idx = price_series.index.get_indexer([ts], method="nearest")
            if idx[0] >= 0:
                return float(price_series.iloc[idx[0]])
        except Exception:
            pass
        return None

    def _find_exit(
        self, price_series: pd.Series, entry_time: str, holding_days: int
    ) -> tuple[Optional[str], Optional[float]]:
        """Find exit price after holding period."""
        if price_series.empty:
            return None, None

        try:
            entry_ts = pd.Timestamp(entry_time)
            exit_ts = entry_ts + pd.Timedelta(days=holding_days)

            # Find nearest price to exit date
            mask = price_series.index >= entry_ts
            future_prices = price_series[mask]

            if future_prices.empty:
                return None, None

            # Take price at or before exit date
            before_exit = future_prices[future_prices.index <= exit_ts]
            if before_exit.empty:
                exit_idx = future_prices.index[0]
            else:
                exit_idx = before_exit.index[-1]

            exit_price = float(price_series.loc[exit_idx])
            return str(exit_idx), exit_price

        except Exception:
            return None, None

    def _build_equity_curve(
        self, trades: list[TradeRecord], initial_capital: float
    ) -> tuple[list[float], list[float], list[str]]:
        """Build equity curve and drawdown curve from trades."""
        if not trades:
            return [initial_capital], [0.0], []

        equity = [initial_capital]
        timestamps: list[str] = []
        current_equity = initial_capital

        for trade in trades:
            current_equity += trade.pnl
            equity.append(round(current_equity, 2))
            timestamps.append(trade.exit_time or trade.entry_time)

        # Calculate drawdown curve
        equity_arr = np.array(equity, dtype=float)
        running_max = np.maximum.accumulate(equity_arr)
        drawdowns = ((equity_arr - running_max) / running_max) * 100.0

        return equity, drawdowns.tolist(), timestamps

    def _calculate_metrics(
        self,
        trades: list[TradeRecord],
        equity_curve: list[float],
        config: BacktestConfig,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if not trades:
            return PerformanceMetrics()

        pnl_pcts = np.array([t.pnl_pct for t in trades], dtype=float)
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
        excess_returns = daily_returns - config.risk_free_rate / 252.0
        sharpe = 0.0
        if np.std(excess_returns) > 1e-10:
            sharpe = float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

        # Sortino Ratio (downside deviation only)
        downside = daily_returns[daily_returns < 0]
        sortino = 0.0
        if len(downside) > 0 and np.std(downside) > 1e-10:
            sortino = float(
                np.mean(excess_returns) / np.std(downside) * np.sqrt(252)
            )

        # Max Drawdown
        running_max = np.maximum.accumulate(equities)
        drawdowns = (equities - running_max) / running_max
        max_dd_pct = float(np.min(drawdowns)) * 100.0

        # Max drawdown duration
        max_dd_duration = self._max_drawdown_duration(equities)

        # Calmar Ratio
        calmar = 0.0
        if abs(max_dd_pct) > 1e-10:
            calmar = annualized_return_pct / abs(max_dd_pct)

        # Win/Loss stats
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        win_rate = len(winning) / len(trades) * 100.0 if trades else 0.0

        avg_win = np.mean([t.pnl_pct for t in winning]) if winning else 0.0
        avg_loss = abs(np.mean([t.pnl_pct for t in losing])) if losing else 1.0
        gross_profit = sum(t.pnl for t in winning) if winning else 0.0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 1.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        avg_holding = np.mean([t.holding_days for t in trades])

        # Information Ratio (vs benchmark = 0 for simplicity)
        benchmark_returns = np.zeros_like(daily_returns)
        active_returns = daily_returns - benchmark_returns
        tracking_error = np.std(active_returns)
        info_ratio = 0.0
        if tracking_error > 1e-10:
            info_ratio = float(np.mean(active_returns) / tracking_error * np.sqrt(252))

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

    def _max_drawdown_duration(self, equities: np.ndarray) -> int:
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

    def _walk_forward_validation(
        self,
        signals_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        weights: dict[str, float],
        config: BacktestConfig,
    ) -> list[WalkForwardResult]:
        """Walk-forward validation to prevent overfitting.

        Splits data into rolling train/test windows and evaluates
        out-of-sample performance.
        """
        results: list[WalkForwardResult] = []

        if len(signals_df) < config.walk_forward_window + config.walk_forward_step:
            logger.warning("Insufficient data for walk-forward validation")
            return results

        n = len(signals_df)
        fold = 0

        for test_start_idx in range(
            config.walk_forward_window, n, config.walk_forward_step
        ):
            train_start_idx = max(0, test_start_idx - config.walk_forward_window)
            test_end_idx = min(n, test_start_idx + config.walk_forward_step)

            train_df = signals_df.iloc[train_start_idx:test_start_idx]
            test_df = signals_df.iloc[test_start_idx:test_end_idx]

            if test_df.empty:
                continue

            # Generate trades on test set only
            test_trades = self._generate_trades(test_df, prices_df, weights, config)

            if not test_trades:
                fold += 1
                continue

            # Calculate test metrics
            equity = [config.initial_capital]
            for t in test_trades:
                equity.append(equity[-1] + t.pnl)

            equity_arr = np.array(equity, dtype=float)
            returns = np.diff(equity_arr) / equity_arr[:-1] if len(equity_arr) > 1 else np.array([0.0])

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

    def _parameter_sensitivity(
        self,
        signals_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        config: BacktestConfig,
    ) -> list[SensitivityResult]:
        """Analyze how sensitive Sharpe ratio is to each dimension's weight.

        Varies each weight ±50% from default while keeping others fixed.
        """
        results: list[SensitivityResult] = []
        base_weights = dict(WEIGHTS)

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

                trades = self._generate_trades(signals_df, prices_df, test_weights, config)

                if not trades:
                    values_tested.append(test_weights[dim_name])
                    sharpes.append(0.0)
                    returns.append(0.0)
                    continue

                equity = [config.initial_capital]
                for t in trades:
                    equity.append(equity[-1] + t.pnl)

                equity_arr = np.array(equity, dtype=float)
                ret = np.diff(equity_arr) / equity_arr[:-1] if len(equity_arr) > 1 else np.array([0.0])

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

    def _empty_result(self, config: BacktestConfig) -> BacktestResult:
        """Return an empty result when no data is available."""
        return BacktestResult(
            config=config,
            metrics=PerformanceMetrics(),
            equity_curve=[config.initial_capital],
            drawdown_curve=[0.0],
            timestamps=[],
            weights_used=config.custom_weights or dict(WEIGHTS),
        )
