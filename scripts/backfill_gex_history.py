#!/usr/bin/env python3
"""
Backfill gex_history table from SqueezeMetrics public CSV.

Source: https://squeezemetrics.com/monitor/static/DIX.csv
Format: date,price,dix,gex  (date YYYY-MM-DD, SPY ETF price, DIX ratio, GEX $)
History: ~15 years (3832 rows as of 2026-07-28)

Fills last N days (default 90) into `gex_history` table:
    timestamp          DATETIME PRIMARY KEY,
    gex_local          REAL NOT NULL,
    gex_calibrated     REAL,
    alpha_factor       REAL,
    put_wall_level     REAL,
    flip_zone_lower    REAL,
    flip_zone_upper    REAL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP

Usage:
    python scripts/backfill_gex_history.py --days 90
    python scripts/backfill_gex_history.py --days 365 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "resonance.db"

SQUEEZEMETRICS_CSV_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
USER_AGENT = "Mozilla/5.0 (compatible; MSR-1-Backfill/1.0; +https://github.com/raymodny-ai/Multi-source-Resonance-1)"

# Column mappings
COL_DATE = 0
COL_PRICE = 1
COL_DIX = 2
COL_GEX = 3

# GEX calibration ratio (matches squeezemetrics_fetcher.py: `gex_calibrated = gex_local * 0.95`)
GEX_CALIBRATION_RATIO = 0.95

# Default alpha factor when not derivable from CSV
DEFAULT_ALPHA = 1.0

# Flip zone heuristic: SPY ETF put-wall ~0.96 × price, flip zone 0.97–1.03 × price
PUT_WALL_RATIO = 0.96
FLIP_ZONE_LOWER_RATIO = 0.97
FLIP_ZONE_UPPER_RATIO = 1.03


def fetch_csv(url: str = SQUEEZEMETRICS_CSV_URL) -> list[list[str]]:
    """Download SqueezeMetrics DIX.csv and return parsed rows (excl. header)."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows or rows[0][0] != "date":
        raise ValueError(f"unexpected CSV header: {rows[0] if rows else 'empty'}")
    return rows[1:]  # strip header


def filter_last_n_days(rows: Iterable[list[str]], days: int) -> list[list[str]]:
    """Keep only rows within the last N calendar days (trading days ≈)."""
    cutoff = (datetime.now() - timedelta(days=days)).date()
    out = []
    for r in rows:
        try:
            d = datetime.strptime(r[COL_DATE], "%Y-%m-%d").date()
        except (ValueError, IndexError):
            continue
        if d >= cutoff:
            out.append(r)
    return out


def row_to_gex_history(r: list[str]) -> tuple | None:
    """Map CSV row → gex_history INSERT tuple.

    Returns None if row is malformed or all-numeric columns are NaN/empty.
    """
    try:
        date_str = r[COL_DATE]
        price = float(r[COL_PRICE])
        gex_raw = float(r[COL_GEX])
    except (IndexError, ValueError):
        return None

    # Skip rows where price/gex are NaN or zero (defensive)
    if price <= 0 or gex_raw == 0.0:
        return None

    timestamp = f"{date_str} 00:00:00"
    gex_local = gex_raw
    gex_calibrated = gex_raw * GEX_CALIBRATION_RATIO
    alpha = DEFAULT_ALPHA
    put_wall = round(price * PUT_WALL_RATIO, 2)
    flip_lower = round(price * FLIP_ZONE_LOWER_RATIO, 2)
    flip_upper = round(price * FLIP_ZONE_UPPER_RATIO, 2)

    return (timestamp, gex_local, gex_calibrated, alpha, put_wall, flip_lower, flip_upper)


def upsert_gex_history(db_path: Path, rows: list[tuple]) -> tuple[int, int]:
    """Insert/replace rows into gex_history. Returns (inserted, skipped)."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        inserted = 0
        skipped = 0
        # Use INSERT OR REPLACE so re-running backfill is idempotent
        cur.executemany(
            """INSERT OR REPLACE INTO gex_history
               (timestamp, gex_local, gex_calibrated, alpha_factor,
                put_wall_level, flip_zone_lower, flip_zone_upper, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            rows,
        )
        inserted = cur.rowcount
        conn.commit()
        return inserted, skipped
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=90, help="Number of past days to backfill (default 90)")
    parser.add_argument("--db", type=Path, default=DB_PATH, help=f"Path to SQLite db (default: {DB_PATH})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted, do not write")
    parser.add_argument("--url", default=SQUEEZEMETRICS_CSV_URL, help="Override CSV URL (for testing)")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"❌ DB not found: {args.db}", file=sys.stderr)
        return 1

    print(f"[1/4] Fetching CSV from {args.url} ...")
    try:
        all_rows = fetch_csv(args.url)
    except Exception as e:
        print(f"❌ CSV fetch failed: {e}", file=sys.stderr)
        return 2
    print(f"      downloaded {len(all_rows)} rows")

    print(f"[2/4] Filtering last {args.days} days ...")
    recent = filter_last_n_days(all_rows, args.days)
    print(f"      {len(recent)} rows match")

    if not recent:
        print("⚠ no rows in range — check date format or --days value")
        return 0

    print(f"[3/4] Mapping to gex_history schema ...")
    mapped: list[tuple] = []
    skipped_map = 0
    for r in recent:
        m = row_to_gex_history(r)
        if m is None:
            skipped_map += 1
            continue
        mapped.append(m)
    print(f"      {len(mapped)} mappable, {skipped_map} skipped (NaN/zero)")

    if args.dry_run:
        print(f"[4/4] DRY RUN — first 3 rows would be:")
        for row in mapped[:3]:
            print(f"      {row}")
        print(f"      ... and {max(0, len(mapped) - 3)} more")
        return 0

    print(f"[4/4] Writing to {args.db} ...")
    inserted, _ = upsert_gex_history(args.db, mapped)
    print(f"      ✅ inserted/replaced {inserted} rows")

    # Show summary
    conn = sqlite3.connect(args.db)
    try:
        total = conn.execute("SELECT COUNT(*) FROM gex_history").fetchone()[0]
        rng = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM gex_history").fetchone()
        print(f"\n=== gex_history now ===")
        print(f"  total rows: {total}")
        print(f"  range:      {rng[0]} .. {rng[1]}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())