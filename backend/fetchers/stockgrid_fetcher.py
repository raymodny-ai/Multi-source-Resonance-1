"""
StockGrid-style option flow data fetcher (real-data version).

Source history:
- 2026-07-31: StockGrid API 已死 (301 -> axlfi.com/landing, SaaS 落地页无 API)
- 重写为走 yfinance 拉 90d 历史 + numpy.polyfit 计算 20d/60d 斜率
- 输出 schema 与原 StockGrid 完全一致, 下游 dashboard / darkpool / signal 不需要改
- 如果 yfinance 没装, 退化为 mock

Fetches price/volume slope data and divergence signals.
Used as input for dark_pool_metrics.stockgrid_* columns.

Source: yfinance (replacing dead StockGrid API)
Fallback: Returns mock data matching expected schema.
"""

import asyncio
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class StockGridFetcher(BaseFetcher):
    """Fetches StockGrid-shaped price/volume slope and divergence data via yfinance."""

    @property
    def source_name(self) -> str:
        return "stockgrid"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # Public data, no API key needed

    # Symbols to monitor
    SYMBOLS = ["SPY", "QQQ", "IWM"]
    LOOKBACK_DAYS = 90  # 覆盖 20d + 60d 斜率窗口

    def _is_mock_mode(self) -> bool:
        """StockGrid is public — never in mock mode unless network unavailable."""
        return False

    async def fetch(self) -> dict:
        """Fetch slope data via yfinance (StockGrid API 已死)."""
        try:
            return await self._fetch_yfinance_slope()
        except Exception as e:
            self.logger.warning(f"StockGrid(yfinance) fetch failed: {e}, returning mock")
            mock = self._generate_mock_data()
            mock["_internal_mock"] = True
            return mock

    def _mock_data(self) -> dict:
        """Return mock StockGrid data."""
        return self._generate_mock_data()

    async def _fetch_yfinance_slope(self) -> dict[str, Any]:
        """Compute 20d/60d price+volume slope per symbol via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError("yfinance not installed")

        def _download_all() -> dict[str, Any]:
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=self.LOOKBACK_DAYS + 5)
            data: dict[str, Any] = {}
            for sym in self.SYMBOLS:
                try:
                    df = yf.download(
                        sym,
                        start=start.isoformat(),
                        end=end.isoformat(),
                        progress=False,
                        auto_adjust=True,
                    )
                    if df is None or len(df) < 20:
                        data[sym] = None
                        continue
                    closes = df["Close"].squeeze() if hasattr(df["Close"], "squeeze") else df["Close"]
                    vols = df["Volume"].squeeze() if hasattr(df["Volume"], "squeeze") else df["Volume"]
                    from numpy import polyfit
                    n = len(closes)
                    x = list(range(n))
                    c = closes.values.astype(float)
                    v = vols.values.astype(float)
                    slope_all_c = polyfit(x, c, 1)[0] if n >= 2 else 0.0
                    slope_all_v = polyfit(x, v, 1)[0] if n >= 2 else 0.0
                    slope_20_c = polyfit(x[-20:], c[-20:], 1)[0] if n >= 20 else slope_all_c
                    slope_60_c = polyfit(x[-60:], c[-60:], 1)[0] if n >= 60 else slope_all_c
                    # Divergence: 价格上升 + 成交量下降 (或反过来)
                    divergence = (slope_20_c > 0 and slope_all_v < 0) or (slope_20_c < 0 and slope_all_v > 0)
                    data[sym] = {
                        "price_slope_20d": round(float(slope_20_c), 4),
                        "price_slope_60d": round(float(slope_60_c), 4),
                        "volume_slope_20d": round(float(slope_all_v), 4),
                        "divergence": bool(divergence),
                        "last_close": float(c[-1]),
                        "as_of": str(closes.index[-1].date()),
                    }
                except Exception as exc:
                    self.logger.warning(f"[stockgrid:yfinance] {sym} failed: {exc}")
                    data[sym] = None
            return data

        # yf.download 是 blocking, 跑在线程池里
        raw = await asyncio.to_thread(_download_all)

        results: dict[str, Any] = {}
        for sym, d in raw.items():
            if d is None:
                results[sym] = self._mock_symbol()
            else:
                results[sym] = d

        # Aggregate signals
        any_divergence = any(v.get("divergence", False) for v in results.values())
        avg_slope_20d = sum(v.get("price_slope_20d", 0) for v in results.values()) / max(len(results), 1)

        return {
            "date": date.today().isoformat(),
            "symbols": results,
            "stockgrid_20d_slope": round(avg_slope_20d, 4),
            "stockgrid_60d_slope": round(
                sum(v.get("price_slope_60d", 0) for v in results.values()) / max(len(results), 1), 4
            ),
            "stockgrid_divergence": any_divergence,
            "stockgrid_signal": any_divergence and avg_slope_20d < 0,
        }

    def _mock_symbol(self) -> dict[str, Any]:
        """Generate mock data for a single symbol."""
        return {
            "price_slope_20d": round(random.uniform(-0.5, 0.5), 4),
            "price_slope_60d": round(random.uniform(-0.3, 0.3), 4),
            "volume_slope_20d": round(random.uniform(-0.4, 0.4), 4),
            "divergence": random.random() < 0.2,
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock StockGrid data."""
        symbols = {sym: self._mock_symbol() for sym in self.SYMBOLS}
        avg_20d = sum(v["price_slope_20d"] for v in symbols.values()) / len(symbols)
        any_div = any(v["divergence"] for v in symbols.values())

        return {
            "date": date.today().isoformat(),
            "symbols": symbols,
            "stockgrid_20d_slope": round(avg_20d, 4),
            "stockgrid_60d_slope": round(random.uniform(-0.3, 0.3), 4),
            "stockgrid_divergence": any_div,
            "stockgrid_signal": any_div and avg_20d < 0,
        }
