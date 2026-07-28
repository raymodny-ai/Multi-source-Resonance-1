#!/usr/bin/env python
"""
Backfill vix_term_structure with 2+ years of FRED VIXCLS + VXVCLS history.

CBOE CDN 403 blocks live VIX/VXV fetches. FRED's public CSV endpoint doesn't
need an API key and has 670+ rows (~2.7 years) of daily history.

Usage:
    .venv/bin/python scripts/backfill_vix_term_structure.py [--days 730]
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

# Allow running from workspace root
WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))

from backend.config import settings  # noqa: E402
from backend.database import get_db  # noqa: E402

FRED_VIXCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
FRED_VXVCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS"

CONTANGO_THRESHOLD = 0.02
BACKWARDATION_THRESHOLD = -0.02


def _regime(vix_spot: float) -> str:
    if vix_spot < 15.0:
        return "low"
    if vix_spot < 25.0:
        return "normal"
    if vix_spot < 35.0:
        return "elevated"
    return "panic"


def fetch_fred_series(url: str) -> dict[str, float]:
    """Parse FRED CSV → {date_str: value} dict (skip missing)."""
    try:
        with urlopen(url, timeout=15) as r:
            text = r.read().decode()
    except Exception as e:
        print(f"FRED fetch error for {url}: {e}")
        return {}
    result = {}
    for line in text.strip().split("\n")[1:]:  # skip header
        if "," not in line:
            continue
        d, v = line.split(",", 1)
        d, v = d.strip(), v.strip()
        if v == "." or not v:
            continue
        try:
            result[d] = float(v)
        except ValueError:
            continue
    return result


async def main(days: int = 730) -> None:
    print(f"Fetching FRED VIXCLS + VXVCLS...")
    vix_series = fetch_fred_series(FRED_VIXCLS_URL)
    vxv_series = fetch_fred_series(FRED_VXVCLS_URL)
    print(f"  VIXCLS: {len(vix_series)} rows")
    print(f"  VXVCLS: {len(vxv_series)} rows")

    # Align dates
    common_dates = sorted(set(vix_series.keys()) & set(vxv_series.keys()))
    if not common_dates:
        print("No common dates between VIXCLS and VXVCLS — aborting")
        return

    # Limit to last N days
    cutoff_date = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if days == 0
        else (
            datetime.fromisoformat(common_dates[-1])
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    )
    if days > 0:
        # Filter to last N days
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        recent_dates = [d for d in common_dates if d >= cutoff_str]
    else:
        recent_dates = common_dates

    print(f"Inserting {len(recent_dates)} daily rows into vix_term_structure...")

    rows_inserted = 0
    async with get_db() as db:
        for d in recent_dates:
            vix_spot = vix_series[d]
            vxv = vxv_series[d]
            ratio = (vxv / vix_spot - 1.0) if vix_spot else 0.0
            if ratio > CONTANGO_THRESHOLD:
                state = "contango"
            elif ratio < BACKWARDATION_THRESHOLD:
                state = "backwardation"
            else:
                state = "flat"
            panic_premium = vix_spot - vxv
            regime = _regime(vix_spot)

            await db.execute(
                """INSERT OR REPLACE INTO vix_term_structure
                   (date, vix_spot, vx_3m_proxy, term_structure_ratio,
                    term_structure_state, panic_premium, regime, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (d, vix_spot, vxv, round(ratio, 4),
                 state, round(panic_premium, 4), regime),
            )
            rows_inserted += 1
        await db.commit()

    print(f"✓ {rows_inserted} rows inserted into vix_term_structure")

    # Show last 5
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT date, vix_spot, vx_3m_proxy, term_structure_ratio,
                      term_structure_state, panic_premium, regime
               FROM vix_term_structure ORDER BY date DESC LIMIT 5"""
        )
        rows = await cursor.fetchall()
        print("\nLast 5 entries:")
        print(f"  {'date':12s} {'vix_spot':>9s} {'vx_3m':>7s} {'ratio':>7s} {'state':>14s} {'panic':>7s} {'regime':>10s}")
        for r in rows:
            d, v, v3m, ratio, state, panic, regime = r
            print(f"  {d:12s} {v:9.2f} {v3m:7.2f} {ratio*100:6.2f}% {state:>14s} {panic:+6.2f} {regime:>10s}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=730,
                        help="Number of days to backfill (default 730 = 2 years)")
    args = parser.parse_args()
    asyncio.run(main(args.days))