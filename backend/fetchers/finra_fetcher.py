"""
FINRA short interest data fetcher (real-data fallback path).

Source history:
- 2026-07-31: FINRA 公开 API (api.finra.org/data/groups/shortInterest) 全部 404
  (FINRA 2023 后下线开放 API, 仅限内部/受邀访问)
- 重写: 优先尝试 FINRA API (兼容保留), 失败走 yfinance .info['shortPercentOfFloat']
- yfinance 拿不到 (ETF 类没 short data) 才 mock

Fetches short interest and days-to-cover data.
Fallback chain: FINRA API -> yfinance .info -> mock.
"""

import asyncio
import random
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.fetchers.base import BaseFetcher


class FinraFetcher(BaseFetcher):
    """Fetches short interest data. Real: FINRA -> yfinance .info -> mock."""

    @property
    def source_name(self) -> str:
        return "finra"

    @property
    def _mock_mode_key(self) -> str:
        return "gexmetrix"  # FINRA is public data

    FINRA_API_URL = "https://api.finra.org/data/groups/shortInterest"

    # Monitored symbols (2026-07-31 改为高 short interest 名气股)
    # 原 SPY/QQQ/IWM 全是 ETF — yfinance 无 short data 字段, 永远走 mock
    # 改个股后能拿到真 short_interest / shortRatio / shortPercentOfFloat / dateShortInterest
    SYMBOLS = ["GME", "AMC", "AAPL", "NVDA", "TSLA", "PLTR", "MARA", "RIOT"]

    def _is_mock_mode(self) -> bool:
        """FINRA is public — never in mock mode unless network unavailable."""
        return False

    async def fetch(self) -> dict:
        """Fetch short interest for monitored symbols (FINRA -> yfinance -> mock)."""
        try:
            return await self._fetch_short_interest()
        except Exception as e:
            self.logger.warning(f"FINRA fetch chain failed: {e}, returning mock")
            return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock FINRA short interest data."""
        return self._generate_mock_data()

    async def _fetch_short_interest(self) -> dict[str, Any]:
        """Try FINRA first, fallback to yfinance .info, fallback to mock per-symbol."""
        results: dict[str, Any] = {}

        # Step 1: Try FINRA API (currently 404, but keep code path for future revival)
        try:
            client = await self._get_client()
            for sym in self.SYMBOLS:
                try:
                    resp = await client.get(self.FINRA_API_URL, params={"symbol": sym, "limit": 1}, timeout=4.0)
                    resp.raise_for_status()
                    jd = resp.json()
                    if jd and jd.get("data"):
                        latest = jd["data"][0]
                        results[sym] = {
                            "short_interest": latest.get("shortInterest", 0),
                            "days_to_cover": latest.get("daysToCover", 0),
                            "settlement_date": latest.get("settlementDate", ""),
                            "source": "finra",
                        }
                except Exception:
                    pass  # fall through to yfinance
        except Exception:
            pass

        # Step 2: yfinance .info fallback (only for symbols still missing)
        missing = [s for s in self.SYMBOLS if s not in results]
        if missing:
            yf_results = await asyncio.to_thread(self._yfinance_short_info, missing)
            for sym, info in yf_results.items():
                if info is not None:
                    results[sym] = info
                    continue
                results[sym] = {**self._mock_symbol(sym), "source": "mock"}

        # Step 3: any remaining missing -> mock
        for sym in self.SYMBOLS:
            if sym not in results:
                results[sym] = {**self._mock_symbol(sym), "source": "mock"}

        return {
            "date": date.today().isoformat(),
            "symbols": results,
            "aggregated_short_ratio": round(
                sum(v.get("days_to_cover", 0) for v in results.values()) / max(len(results), 1), 2
            ),
        }

    @staticmethod
    def _yfinance_short_info(symbols: list[str]) -> dict[str, Optional[dict]]:
        """Pull shortPercentOfFloat / sharesShort from yfinance .info (blocking, run in thread).

        yfinance .info 真实返回字段 (2026-07-31 验证, 个股 OK, ETF 全部 None):
            sharesShort             — 总空头股数 (例: GME=55,426,276)
            shortRatio              — 回补天数 (例: GME=12.78)
            shortPercentOfFloat     — 空头占流通股比例 (例: GME=0.1354)
            dateShortInterest       — 结算日 epoch (例: 1784073600 = 2026-07-15)
        ETF (SPY/QQQ/IWM) 全部 None — 无公开 short interest, mock 兜底
        """
        out: dict[str, Optional[dict]] = {}
        try:
            import yfinance as yf
        except ImportError:
            return {s: None for s in symbols}

        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                info = t.info or {}
                spf = info.get("shortPercentOfFloat")
                ss = info.get("sharesShort")
                sr = info.get("shortRatio")
                ds_epoch = info.get("dateShortInterest")
                if spf is None and ss is None:
                    out[sym] = None
                    continue
                # 转换 epoch -> ISO date (epoch 是 NYSE 半月中结算日, e.g. 1784073600 = 2026-07-15)
                ds_iso = (
                    datetime.fromtimestamp(int(ds_epoch), tz=timezone.utc).date().isoformat()
                    if ds_epoch else None
                )
                out[sym] = {
                    "short_interest": int(ss) if ss else 0,
                    "short_percent_of_float": round(float(spf), 4) if spf else None,
                    "days_to_cover": round(float(sr), 2) if sr else None,
                    "settlement_date": ds_iso or date.today().isoformat(),
                    "source": "yfinance",
                }
            except Exception:
                out[sym] = None
        return out

    def _mock_symbol(self, symbol: str) -> dict[str, Any]:
        """Generate mock data for a single symbol."""
        return {
            "short_interest": random.randint(5_000_000, 50_000_000),
            "days_to_cover": round(random.uniform(1.0, 5.0), 2),
            "settlement_date": date.today().isoformat(),
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock FINRA short interest data."""
        symbols = {}
        for sym in self.SYMBOLS:
            symbols[sym] = {**self._mock_symbol(sym), "source": "mock"}

        return {
            "date": date.today().isoformat(),
            "symbols": symbols,
            "aggregated_short_ratio": round(random.uniform(1.5, 4.5), 2),
        }
