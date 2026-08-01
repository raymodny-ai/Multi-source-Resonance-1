"""
Unit tests for SignalOutcomeTracker offline consistency fallback
and forward-window defaults (IMPL-BAYESIAN-001 #3, #5).
"""
import pytest

import aiosqlite

from backend.quant.signal_outcomes import SignalOutcomeTracker, FORWARD_DAYS


def test_forward_days_now_3():
    """IMPL-BAYESIAN-001 #5: cold-start window shortened 5 -> 3."""
    assert FORWARD_DAYS == 3


@pytest.mark.asyncio
async def test_consistency_fallback_tags_but_never_fabricates_outcome():
    """IMPL-BAYESIAN-001 #3: offline fallback tags resonance but keeps
    ``outcome`` NULL so fake profit/loss never enters Bayesian learning."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("""
        CREATE TABLE signal_alerts (
            id                INTEGER PRIMARY KEY,
            trigger_time      TEXT,
            outcome           TEXT,
            gex_score         REAL,
            vix_score         REAL,
            crypto_score      REAL,
            darkpool_score    REAL,
            outcome_method    TEXT DEFAULT 'spx_forward',
            outcome_checked_at TEXT,
            forward_return    REAL,
            mock_count        INTEGER DEFAULT 0,
            mock_sources      TEXT
        );
    """)
    await db.executemany(
        """INSERT INTO signal_alerts
           (id, trigger_time, gex_score, vix_score, crypto_score,
            darkpool_score, mock_count, mock_sources)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            (1, "2026-07-20T00:00:00", 80, 70, 60, 55, 0, None),  # consistent (>=3 high)
            (2, "2026-07-20T00:00:00", 10, 20, 30, 15, 0, None),  # inconsistent (<=1 high)
            (3, "2026-07-20T00:00:00", 80, 70, 60, 20, 0, None),  # consistent (3 high)
            (4, "2026-07-20T00:00:00", 60, 60, 20, 20, 0, None),  # ambiguous (2 high) -> skip
            (5, "2026-07-20T00:00:00", 80, 70, 60, 55, 2, "[]"),  # mock -> excluded
        ],
    )
    await db.commit()

    try:
        tracker = SignalOutcomeTracker(forward_days=8)
        results = await tracker._check_consistency_fallback(db)
        markers = {r["id"]: r["marker"] for r in results}
        assert markers == {1: "consistent", 2: "inconsistent", 3: "consistent"}

        cur = await db.execute(
            "SELECT id, outcome, outcome_method, forward_return "
            "FROM signal_alerts ORDER BY id"
        )
        rows = await cur.fetchall()
        row_map = {r["id"]: dict(r) for r in rows}

        # Tagged rows: method set, forward_return 0.0 placeholder, outcome NULL.
        for ident in (1, 2, 3):
            assert row_map[ident]["outcome_method"] == "consistency_fallback"
            assert row_map[ident]["forward_return"] == 0.0
            assert row_map[ident]["outcome"] is None  # never fabricated
        # Skipped rows untouched.
        for ident in (4, 5):
            assert row_map[ident]["outcome_method"] == "spx_forward"
            assert row_map[ident]["outcome"] is None
    finally:
        await db.close()
