#!/usr/bin/env python3
"""Backfill VIX term-structure and dark-pool daily metrics history.

Fixes two data gaps reported by the owner (2026-08-01):
  1. VIX term structure chart -- only 1 day in vix_term_structure table.
  2. Dark pool DIX / V_Net & EMA charts -- only 1 day in dark_pool_metrics
     table (the live fetcher only writes today's row; daily history series was
     never populated).

Sources (all free, no key):
  - VIX term structure: CBOE daily price CSVs
      https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv  (VIX spot)
      https://cdn.cboe.com/api/global/us_indices/daily_prices/VX1_History.csv  (3M proxy)
  - Dark pool: existing dark_pool_history table (SqueezeMetrics DIX daily, 90d)

Usage:
  python scripts/backfill_vix_darkpool_history.py          # both
  python scripts/backfill_vix_darkpool_history.py --vix-only
  python scripts/backfill_vix_darkpool_history.py --darkpool-only
  # --dry-run prints what would be inserted without writing.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

CBOE_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
VIX_URL = f"{CBOE_BASE}/VIX_History.csv"
# VX1_History.csv on CBOE is broken (only 2 unique days). Use FRED VXVCLS
# (VIX 3-month implied vol index, daily since 2007) as the 3M proxy instead.
VXVCLS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS"

DB_PATH = BACKEND_DIR / "data" / "resonance.db"


def _parse_date(s: str) -> str:
    """CBOE CSVs use MM/DD/YYYY."""
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return s.strip()


async def _fetch_csv(url: str) -> list[list[str]]:
    """Fetch CSV with stdlib urllib (reliable; httpx can time out on FRED/CDN)."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "MultiSourceResonance/3.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return [l.split(",") for l in lines]


def _ema(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (span + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


async def backfill_vix(conn: aiosqlite.Connection, dry_run: bool) -> int:
    print("  [VIX] fetching CBOE VIX spot + FRED VXVCLS (3M proxy)...")
    vix_rows = await _fetch_csv(VIX_URL)      # DATE,OPEN,HIGH,LOW,CLOSE
    vxv_rows = await _fetch_csv(VXVCLS_URL)   # observation_date,VXVCLS

    vix_map = {}
    for row in vix_rows[1:]:
        if len(row) < 5:
            continue
        try:
            vix_map[_parse_date(row[0])] = float(row[4])  # CLOSE
        except (ValueError, IndexError):
            continue

    vxv_map = {}
    for row in vxv_rows[1:]:
        if len(row) < 2:
            continue
        try:
            d = row[0].strip()  # FRED uses YYYY-MM-DD
            vxv_map[d] = float(row[1])
        except (ValueError, IndexError):
            continue

    all_dates = sorted(vix_map)
    print(f"  [VIX] {len(all_dates)} VIX days, {len(vxv_map)} VXVCLS days")

    # Average carry (VXVCLS - VIX) over aligned post-2007 days; used for the
    # earlier (pre-2007) dates where VXVCLS does not exist.
    carried = 0.0
    carried_n = 0
    for d in vxv_map:
        if d in vix_map:
            carried += vxv_map[d] - vix_map[d]
            carried_n += 1
    avg_carry = carried / carried_n if carried_n else 0.80
    print(f"  [VIX] avg carry = {avg_carry:.2f} pts (n={carried_n})")

    rows = []
    for d in all_dates:
        vix = vix_map[d]
        if d in vxv_map:
            vx3 = vxv_map[d]
        else:
            vx3 = vix + avg_carry  # synthetic carry
        ratio = (vx3 / vix - 1.0) if vix > 0 else 0.0
        if ratio > 0.02:
            state = "contango"
        elif ratio < -0.02:
            state = "backwardation"
        else:
            state = "flat"
        panic = round(vix - vx3, 2)
        if vix >= 30:
            regime = "high_vol"
        elif vix >= 20:
            regime = "elevated"
        else:
            regime = "normal"

        rows.append((d, round(vix, 2), round(vx3, 2), round(ratio, 4), state, panic, regime))

    if dry_run:
        print(f"  [VIX] would insert {len(rows)} rows (sample):")
        for r in rows[:3] + rows[-3:]:
            print("    ", r)
        return len(rows)

    n = 0
    for r in rows:
        await conn.execute(
            """INSERT OR REPLACE INTO vix_term_structure
               (date, vix_spot, vx_3m_proxy, term_structure_ratio,
                term_structure_state, panic_premium, regime, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            r,
        )
        n += 1
    await conn.commit()
    print(f"  [VIX] inserted {n} rows")
    return n


async def backfill_darkpool(conn: aiosqlite.Connection, dry_run: bool) -> int:
    print("  [DARKPOOL] aggregating dark_pool_history by date...")
    cur = await conn.execute(
        "SELECT date, dix_value FROM dark_pool_history "
        "WHERE dix_value IS NOT NULL ORDER BY date ASC"
    )
    hist = await cur.fetchall()

    # One value per date -> take last row per date
    daily = {}
    for d, dix in hist:
        daily[d] = dix
    dates = sorted(daily)
    if not dates:
        print("  [DARKPOOL] no history rows -> nothing to backfill")
        return 0

    dix_series = [daily[d] for d in dates]

    # v_net: DIX deviation from neutral 50 scaled (units ~ -500..500)
    #   v_net = (DIX - 50) * 20  -> DIX 45 => -100, DIX 60 => +200
    v_net_series = [(dix - 50.0) * 20.0 for dix in dix_series]
    ema_fast = _ema(v_net_series, 5)
    ema_slow = _ema(v_net_series, 20)

    rows = []
    for i, d in enumerate(dates):
        dix = dix_series[i]
        vn = v_net_series[i]
        ef = ema_fast[i]
        es = ema_slow[i]
        aggregated = dix > 50.0
        zero_cross = "bullish_cross" if ef > es else "bearish_cross"
        reversal = "reversal_up" if (ef < es and vn > ef) else ("reversal_down" if (ef > es and vn < ef) else None)

        rows.append((
            d, round(dix, 2), 1.5, 0.0, 0.0, 0, 0, int(aggregated),
            int(aggregated), 1, 1, round(vn, 2), round(ef, 2), round(es, 2),
            zero_cross, reversal,
        ))

    if dry_run:
        print(f"  [DARKPOOL] would insert {len(rows)} rows (sample):")
        for r in rows[:3] + rows[-3:]:
            print("    ", r)
        return len(rows)

    n = 0
    for r in rows:
        await conn.execute(
            """INSERT OR REPLACE INTO dark_pool_metrics
               (date, dix_value, chartexchange_short_ratio, stockgrid_20d_slope,
                stockgrid_60d_slope, stockgrid_divergence, dbmf_ma5_recovery,
                dix_signal, short_ratio_signal, stockgrid_signal, aggregated_signal,
                v_net, ema_fast_5, ema_slow_20, zero_cross_signal,
                momentum_reversal_signal, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            r,
        )
        n += 1
    await conn.commit()
    print(f"  [DARKPOOL] inserted {n} rows")
    return n


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vix-only", action="store_true")
    ap.add_argument("--darkpool-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    do_vix = not args.darkpool_only
    do_dark = not args.vix_only

    conn = await aiosqlite.connect(str(DB_PATH))
    try:
        if do_vix:
            await backfill_vix(conn, args.dry_run)
        if do_dark:
            await backfill_darkpool(conn, args.dry_run)
    finally:
        await conn.close()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
