"""
Core backtest engine — orchestrates signal replay, metrics, walk-forward,
sensitivity analysis, and visualization data generation.

Migrated from backend/quant/backtest_engine.py with modular decomposition.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

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
    visualization: dict[str, Any] = {}
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
        weights = bt_config.custom_weights or self._default_weights()

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
        trade_dicts = [t.model_dump() for t in trades]
        metrics = calculate_metrics(trade_dicts, equity_curve, bt_config.risk_free_rate)

        # Walk-forward validation
        config_dict = bt_config.model_dump()
        walk_forward = run_walk_forward(
            signals_df, prices_df, weights, config_dict, self._generate_trades, bt_config.initial_capital
        )

        # Parameter sensitivity analysis
        sensitivity = run_sensitivity(
            signals_df, prices_df, weights, config_dict, self._generate_trades, bt_config.initial_capital
        )

        # Visualization data
        viz_data = {
            "equity_curve": build_equity_curve_data(trade_dicts, equity_curve, timestamps).model_dump(),
            "trade_distribution": build_trade_distribution(trade_dicts).model_dump(),
            "walk_forward_comparison": build_walk_forward_comparison(walk_forward).model_dump(),
        }

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
            visualization=viz_data,
        )

        logger.info(
            f"Backtest complete: {metrics.total_trades} trades, "
            f"Sharpe={metrics.sharpe_ratio:.2f}, Return={metrics.total_return_pct:.1f}%"
        )
        return result

    async def _load_historical_data(
        self, config: BacktestConfig
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load signal alerts and price data from database."""
        try:
            from backend.database import get_db

            async with get_db() as db:
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
        config: Any,
    ) -> list[TradeRecord]:
        """Generate trades from signal triggers."""
        trades: list[TradeRecord] = []

        if signals_df.empty:
            return trades

        # Filter for meaningful signals (LEVEL_2 or LEVEL_3)
        signal_mask = signals_df["alert_level"].isin(["LEVEL_2", "LEVEL_3"])
        active_signals = signals_df[signal_mask].copy()

        if active_signals.empty:
            return trades

        price_series = self._build_price_series(prices_df)
        holding_period = 5

        for _, row in active_signals.iterrows():
            entry_time = row.get("trigger_time", "")
            score = float(row.get("total_score", 0))
            level = str(row.get("alert_level", "LEVEL_0"))

            entry_price = self._lookup_price(price_series, str(entry_time))
            if entry_price is None or entry_price <= 0:
                continue

            exit_time, exit_price = self._find_exit(
                price_series, str(entry_time), holding_period
            )

            if exit_price is None:
                continue

            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price) * 100.0

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

        price_col = "gex_calibrated" if "gex_calibrated" in prices_df.columns else "gex_local"
        series = prices_df.set_index("timestamp")[price_col].dropna()
        series.index = pd.to_datetime(series.index)
        return series.sort_index()

    def _lookup_price(self, price_series: pd.Series, timestamp: str) -> Optional[float]:
        """Look up the nearest price for a given timestamp."""
        if price_series.empty:
            return None

        try:
            ts = pd.Timestamp(timestamp)
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

            mask = price_series.index >= entry_ts
            future_prices = price_series[mask]

            if future_prices.empty:
                return None, None

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

        equity_arr = np.array(equity, dtype=float)
        running_max = np.maximum.accumulate(equity_arr)
        drawdowns = ((equity_arr - running_max) / running_max) * 100.0

        return equity, drawdowns.tolist(), timestamps

    def _default_weights(self) -> dict[str, float]:
        """Get default dimension weights."""
        try:
            from backend.quant.scoring import WEIGHTS
            return dict(WEIGHTS)
        except ImportError:
            return {
                "net_gex_positive": 1.50,
                "zero_gamma_above_spot": 0.50,
                "call_wall_proximity": 0.50,
                "term_structure_contango": 1.00,
                "panic_premium_low": 0.50,
                "leverage_cleanup": 1.00,
                "funding_anomaly": 0.50,
                "oi_crash": 0.50,
                "dix_bullish": 1.00,
                "short_ratio_extreme": 0.50,
                "momentum_reversal": 0.50,
            }

    def _empty_result(self, config: BacktestConfig) -> BacktestResult:
        """Return an empty result when no data is available."""
        return BacktestResult(
            config=config,
            metrics=PerformanceMetrics(),
            equity_curve=[config.initial_capital],
            drawdown_curve=[0.0],
            timestamps=[],
            weights_used=config.custom_weights or self._default_weights(),
        )
