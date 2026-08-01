"""
Signal outcome tracking and false positive rate calculation.

Evaluates historical signal accuracy by comparing signal trigger prices
with subsequent market performance (forward return over N days).
A signal is considered a 'profit' if the forward return is positive,
'loss' otherwise.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Default forward-looking window (calendar days) to evaluate outcome
FORWARD_DAYS = 5


class SignalOutcomeTracker:
    """Signal result tracking and false positive rate calculation."""

    def __init__(self, forward_days: int = FORWARD_DAYS):
        self.forward_days = forward_days

    # ── Core: evaluate unaudited signals ──────────────────────────────────────

    async def check_outcomes(self, db: aiosqlite.Connection) -> list:
        """Check unaudited signals and compute forward return.

        For each signal where outcome IS NULL and trigger_time is at least
        `forward_days` in the past, fetch the SPX close at trigger date and
        at trigger_date + forward_days, then compute:
          - forward_return = (price_after - price_at) / price_at
          - outcome = 'profit' if forward_return > 0 else 'loss'

        Returns:
            list of dicts with keys: id, trigger_time, forward_return, outcome
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed — cannot compute outcomes")
            return []

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.forward_days)
        ).isoformat()

        cursor = await db.execute("""
            SELECT id, trigger_time
            FROM signal_alerts
            WHERE outcome IS NULL
              AND trigger_time <= ?
            ORDER BY trigger_time ASC
        """, (cutoff,))
        rows = await cursor.fetchall()

        if not rows:
            logger.debug("No unaudited signals to evaluate")
            return []

        # Fetch SPX history covering the full range needed
        earliest = min(r["trigger_time"] for r in rows)
        latest = max(r["trigger_time"] for r in rows)
        start = (datetime.fromisoformat(earliest) - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (
            datetime.fromisoformat(latest) + timedelta(days=self.forward_days + 2)
        ).strftime("%Y-%m-%d")

        try:
            # yfinance is synchronous network I/O — run it in a worker thread so
            # it does not block the async event loop (report H-04).
            def _fetch_spx() -> dict:
                ticker = yf.Ticker("^GSPC")
                hist = ticker.history(start=start, end=end)
                if hist.empty:
                    return {}
                return {
                    d.strftime("%Y-%m-%d"): float(row["Close"])
                    for d, row in hist.iterrows()
                }

            close_map: dict[str, float] = await asyncio.to_thread(_fetch_spx)
            if not close_map:
                logger.warning("yfinance returned no SPX data for outcome check")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch SPX history for outcomes: {e}")
            return []

        results = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in rows:
            sig_id = row["id"]
            trigger_dt = row["trigger_time"]
            trigger_date = trigger_dt[:10]  # 'YYYY-MM-DD'

            trigger_price = self._nearest_close(close_map, trigger_date)
            if trigger_price is None:
                continue

            # Target evaluation date
            target_date = (
                datetime.fromisoformat(trigger_date) + timedelta(days=self.forward_days)
            ).strftime("%Y-%m-%d")
            after_price = self._nearest_close(close_map, target_date, lookback=3)
            if after_price is None:
                continue

            fwd_return = (after_price - trigger_price) / trigger_price
            outcome = "profit" if fwd_return > 0 else "loss"

            await db.execute(
                """UPDATE signal_alerts
                   SET outcome = ?, forward_return = ?, outcome_checked_at = ?
                   WHERE id = ?""",
                (outcome, round(fwd_return, 6), now_iso, sig_id),
            )

            results.append({
                "id": sig_id,
                "trigger_time": trigger_dt,
                "forward_return": round(fwd_return, 6),
                "outcome": outcome,
            })

        if results:
            await db.commit()
            logger.info(f"Evaluated {len(results)} signal outcomes")

        return results

    # ── False positive rate ───────────────────────────────────────────────────

    async def get_false_positive_rate(
        self, db: aiosqlite.Connection, days: int = 30
    ) -> float:
        """Compute false positive rate over the last N days.

        False positive rate = loss_count / total_evaluated
        Returns 0.0 if no signals have been evaluated.
        """
        cursor = await db.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses
            FROM signal_alerts
            WHERE outcome IS NOT NULL
              AND outcome_checked_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        row = await cursor.fetchone()
        if not row or row["total"] == 0:
            return 0.0
        return round(row["losses"] / row["total"], 4)

    # ── Performance stats ─────────────────────────────────────────────────────

    async def get_signal_performance(
        self, db: aiosqlite.Connection, days: int = 90
    ) -> dict:
        """Signal performance statistics over the last N days.

        Returns:
            dict with keys:
                total_evaluated, hit_count, miss_count,
                hit_rate, avg_return, max_return, min_return (max drawdown)
        """
        cursor = await db.execute("""
            SELECT
                COUNT(*)                                   AS total_evaluated,
                SUM(CASE WHEN outcome = 'profit' THEN 1 ELSE 0 END) AS hit_count,
                SUM(CASE WHEN outcome = 'loss'   THEN 1 ELSE 0 END) AS miss_count,
                AVG(forward_return)                        AS avg_return,
                MAX(forward_return)                        AS max_return,
                MIN(forward_return)                        AS min_return
            FROM signal_alerts
            WHERE outcome IS NOT NULL
              AND outcome_checked_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        row = await cursor.fetchone()
        if not row or row["total_evaluated"] == 0:
            return {
                "total_evaluated": 0,
                "hit_count": 0,
                "miss_count": 0,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "max_return": 0.0,
                "min_return": 0.0,
            }

        total = row["total_evaluated"]
        hits = row["hit_count"] or 0
        return {
            "total_evaluated": total,
            "hit_count": hits,
            "miss_count": row["miss_count"] or 0,
            "hit_rate": round(hits / total, 4) if total else 0.0,
            "avg_return": round(row["avg_return"] or 0.0, 6),
            "max_return": round(row["max_return"] or 0.0, 6),
            "min_return": round(row["min_return"] or 0.0, 6),
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _nearest_close(
        close_map: dict[str, float],
        target_date: str,
        lookback: int = 0,
    ) -> Optional[float]:
        """Return close price for target_date, falling back up to `lookback` days."""
        from datetime import date as _date

        dt = datetime.fromisoformat(target_date).date()
        for offset in range(lookback + 1):
            candidate = (dt - timedelta(days=offset)).isoformat()
            if candidate in close_map:
                return close_map[candidate]
        return None
