"""
Options Chain + Greeks Fetcher — yfinance + py_vollib (Black-Scholes local calc).

替代 CBOE DataShop API key 的免费方案:
  - yfinance 抓免费 options chain (含 strike/bid/ask/lastPrice/volume/OI/IV)
  - py_vollib (Black-Scholes) 本地算 Greeks (Delta/Gamma/Theta/Vega)
  - 数据源: Yahoo Finance public, 无需 API key, 无月费
  - 适合: 美股期权 EOD 分析, GEX 计算, Gamma exposure 仪表盘

覆盖标的: SPX/SPY/QQQ/IWM/NDX/VIX (项目 monitor universe)
免费层限制: 15min 延迟 (yfinance 实际), 历史 30 天, 不含盘前盘后极端数据
"""
import logging
import math
from datetime import datetime, timezone, date
from typing import Any

from backend.config import Settings
from backend.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

# 标的 → yfinance ticker
YF_TICKER_MAP = {
    "SPX": "^SPX",       # S&P 500 指数 options (注意: ^GSPC 不行, 没 options)
    "SPY": "SPY",        # SPDR S&P 500 ETF
    "QQQ": "QQQ",        # Invesco QQQ
    "IWM": "IWM",        # iShares Russell 2000
    "NDX": "^NDX",       # Nasdaq 100 (有 options)
    # "VIX": "^VIX"  — VIX 本身没期权, 跳过
}

# 默认要计算的 Greeks 数量 (每侧 ATM ±N strikes)
GREEKS_STRIKES_RANGE = 15

# 默认无风险利率 (10Y Treasury 估算, 美联储 funds rate 5.25% - 0.5% term premium)
# 实际项目应接入 FRED DGS10, 暂用静态 fallback
RISK_FREE_RATE_FALLBACK = 0.045


class OptionsChainGreeksFetcher(BaseFetcher):
    """抓 options chain → 本地算 Greeks, 0 成本替代 CBOE API."""

    def __init__(self, config: Settings, db: Any = None) -> None:
        super().__init__(config, db)
        self._ticker_map = YF_TICKER_MAP
        self._strikes_range = GREEKS_STRIKES_RANGE

    # ── Abstract interface implementation ─────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "options_greeks"

    @property
    def _mock_mode_key(self) -> str:
        # 用 yfinance 的 key 作判据 (公开数据, 永远 is_mock=False)
        return "yfinance"

    def _is_mock_mode(self) -> bool:
        """yfinance 是公开数据, 除非显式强制 mock 否则总走真实路径."""
        return False

    async def fetch(self) -> dict:
        """抓 yfinance options chain → 本地 Black-Scholes 算 Greeks."""
        try:
            import yfinance as yf
        except ImportError:
            self.logger.error("[options_greeks] yfinance not installed")
            return self._mock_data()

        try:
            from py_vollib.black_scholes import black_scholes
            from py_vollib.black_scholes.greeks.analytical import delta, gamma, vega, theta
        except ImportError:
            self.logger.error("[options_greeks] py_vollib not installed")
            return self._mock_data()

        now = datetime.now(timezone.utc)
        per_symbol: dict[str, Any] = {}

        for symbol, yf_ticker in self._ticker_map.items():
            try:
                t = yf.Ticker(yf_ticker)
                # 1. 当前 spot price
                hist = t.history(period="5d", interval="1d")
                if hist.empty:
                    self.logger.warning(f"[options_greeks] {symbol} no price history")
                    continue
                spot = float(hist.iloc[-1]["Close"])

                # 2. 取 30-45d 到期 (流动性最好, ATM IV 稳定)
                expiries = t.options
                if not expiries:
                    self.logger.warning(f"[options_greeks] {symbol} no options")
                    continue

                target_expiry = self._pick_expiry(expiries)
                if not target_expiry:
                    continue

                # 3. 抓 calls + puts
                chain = t.option_chain(target_expiry)
                calls = chain.calls
                puts = chain.puts

                # 4. 计算 Greeks (ATM ±N strikes)
                greeks_data = self._calc_greeks_for_chain(
                    calls, puts, spot, target_expiry,
                    delta_fn=delta, gamma_fn=gamma, vega_fn=vega, theta_fn=theta,
                )

                per_symbol[symbol] = {
                    "spot": round(spot, 2),
                    "expiry": target_expiry,
                    "days_to_expiry": (
                        datetime.strptime(target_expiry, "%Y-%m-%d").date() - date.today()
                    ).days,
                    "calls_count": len(calls),
                    "puts_count": len(puts),
                    **greeks_data,
                }
                self.logger.info(
                    f"[options_greeks] {symbol}: spot={spot:.2f} expiry={target_expiry} "
                    f"calls={len(calls)} puts={len(puts)} "
                    f"ATM_IV={greeks_data.get('atm_iv', 0):.3f}"
                )
            except Exception as exc:
                self.logger.error(f"[options_greeks] {symbol} failed: {exc}")
                continue

        if not per_symbol:
            return self._mock_data()

        return {
            "fetch_timestamp": now.isoformat(),
            "symbols": per_symbol,
            "_meta": {
                "source": "options_greeks",
                "is_mock": False,
                "fetched_at": now.isoformat(),
                "error": None,
            },
        }

    def _pick_expiry(self, expiries: list[str]) -> str | None:
        """选 30-45d 到期, 没就选最近."""
        today = date.today()
        for exp in expiries:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            days = (exp_date - today).days
            if 25 <= days <= 60:
                return exp
        # fallback: 选最近的
        return expiries[min(2, len(expiries) - 1)] if len(expiries) > 2 else (expiries[0] if expiries else None)

    def _calc_greeks_for_chain(
        self, calls, puts, spot: float, expiry: str,
        delta_fn, gamma_fn, vega_fn, theta_fn,
    ) -> dict[str, Any]:
        """对 ATM ±N strikes 计算 Greeks, 返回汇总 + 几条代表 strike 的细节."""
        exp_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        T = max((exp_date - date.today()).days, 1) / 365.0
        r = RISK_FREE_RATE_FALLBACK

        # ATM strike: 最接近 spot
        all_strikes = sorted(set(calls["strike"].tolist()) & set(puts["strike"].tolist()))
        if not all_strikes:
            return {"atm_iv": 0, "atm_delta_call": 0, "atm_delta_put": 0,
                    "atm_gamma": 0, "atm_vega": 0, "atm_theta": 0, "strikes": []}

        atm_strike = min(all_strikes, key=lambda k: abs(k - spot))
        atm_idx = all_strikes.index(atm_strike)
        lo = max(0, atm_idx - self._strikes_range)
        hi = min(len(all_strikes), atm_idx + self._strikes_range + 1)
        focus_strikes = all_strikes[lo:hi]

        # 找 ATM call/put row
        atm_call = calls[calls["strike"] == atm_strike]
        atm_put = puts[puts["strike"] == atm_strike]
        atm_iv = float(atm_call.iloc[0]["impliedVolatility"]) if not atm_call.empty else 0.0
        if not atm_iv or math.isnan(atm_iv):
            atm_iv = 0.20  # fallback 20% vol

        # ATM Greeks
        atm_delta_call = delta_fn("c", spot, atm_strike, T, r, atm_iv)
        atm_delta_put = delta_fn("p", spot, atm_strike, T, r, atm_iv)
        atm_gamma = gamma_fn("c", spot, atm_strike, T, r, atm_iv)
        atm_vega = vega_fn("c", spot, atm_strike, T, r, atm_iv)
        atm_theta = theta_fn("c", spot, atm_strike, T, r, atm_iv)

        strikes_detail = []
        for K in focus_strikes:
            c_row = calls[calls["strike"] == K]
            p_row = puts[puts["strike"] == K]
            iv = float(c_row.iloc[0]["impliedVolatility"]) if not c_row.empty else atm_iv
            if math.isnan(iv) or iv <= 0:
                iv = atm_iv

            try:
                d_c = delta_fn("c", spot, K, T, r, iv)
                g_c = gamma_fn("c", spot, K, T, r, iv)
                v_c = vega_fn("c", spot, K, T, r, iv)
                th_c = theta_fn("c", spot, K, T, r, iv)
                d_p = delta_fn("p", spot, K, T, r, iv)
            except Exception:
                continue

            strikes_detail.append({
                "strike": round(float(K), 2),
                "call_delta": round(float(d_c), 4),
                "put_delta": round(float(d_p), 4),
                "gamma": round(float(g_c), 6),
                "vega": round(float(v_c), 4),
                "theta": round(float(th_c), 4),
                "iv": round(float(iv), 4),
                "call_oi": int(c_row.iloc[0]["openInterest"]) if not c_row.empty and not math.isnan(c_row.iloc[0]["openInterest"]) else 0,
                "put_oi": int(p_row.iloc[0]["openInterest"]) if not p_row.empty and not math.isnan(p_row.iloc[0]["openInterest"]) else 0,
            })

        return {
            "atm_iv": round(atm_iv, 4),
            "atm_strike": round(float(atm_strike), 2),
            "atm_delta_call": round(float(atm_delta_call), 4),
            "atm_delta_put": round(float(atm_delta_put), 4),
            "atm_gamma": round(float(atm_gamma), 6),
            "atm_vega": round(float(atm_vega), 4),
            "atm_theta": round(float(atm_theta), 4),
            "risk_free_rate": r,
            "strikes": strikes_detail,
        }

    def _mock_data(self) -> dict:
        """Fallback mock (yfinance / py_vollib 不可用时)."""
        return {
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": {},
            "_meta": {
                "source": "options_greeks",
                "is_mock": True,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "error": "yfinance or py_vollib unavailable",
            },
        }