"""
SQLite async database layer using aiosqlite.
Manages connection pool, WAL mode, and full schema (11 tables + 5 views).
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite

from backend.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Connection pool (simple semaphore-based pool for aiosqlite)
# ─────────────────────────────────────────────────────────────────────────────

_POOL_SIZE = 5
_pool: Optional[asyncio.Semaphore] = None
_connections: list[aiosqlite.Connection] = []


def _get_pool() -> asyncio.Semaphore:
    global _pool
    if _pool is None:
        _pool = asyncio.Semaphore(_POOL_SIZE)
    return _pool


async def _create_connection() -> aiosqlite.Connection:
    """Create a new aiosqlite connection with WAL mode and pragmas."""
    db_path = settings.db_absolute_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrent read/write
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA busy_timeout=5000")

    return conn


async def get_connection() -> aiosqlite.Connection:
    """Acquire a connection from the pool."""
    pool = _get_pool()
    await pool.acquire()

    if _connections:
        conn = _connections.pop()
        # Verify connection is still alive
        try:
            await conn.execute("SELECT 1")
            return conn
        except Exception:
            pass

    return await _create_connection()


def release_connection(conn: aiosqlite.Connection) -> None:
    """Return a connection to the pool and release the semaphore slot.

    PIPE-13: the previous version called ``asyncio.create_task`` from
    this synchronous function, which raised ``RuntimeError: no running
    event loop`` at shutdown (the loop is already stopped by then) and
    leaked the connection. We now close the connection synchronously
    instead of scheduling a coroutine — it's cheap, and we can do it
    in a fire-and-forget thread to avoid blocking the caller.
    """
    pool = _get_pool()
    if len(_connections) < _POOL_SIZE:
        _connections.append(conn)
    else:
        # Pool full, close the connection synchronously. PIPE-13:
        # this is a sync function, so we cannot use asyncio.create_task.
        # Run the close in a background thread instead.
        try:
            import threading
            threading.Thread(
                target=lambda: _close_sync(conn),
                daemon=True,
                name="aiosqlite-close",
            ).start()
        except Exception:
            # Last resort: just drop the reference. The OS will reclaim
            # the underlying file handle on process exit.
            pass
    # Always make room for another acquire — the slot belongs to this borrow.
    try:
        pool.release()
    except ValueError:
        # Pool released more than acquired (shouldn't happen) — ignore.
        pass
    _get_pool().release()


def _close_sync(conn: aiosqlite.Connection) -> None:
    """Best-effort sync close of an aiosqlite connection (PIPE-13)."""
    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(conn.close())
        finally:
            loop.close()
    except Exception:
        # Already closed or otherwise unusable — nothing to do.
        pass


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for database access (dependency injection)."""
    conn = await get_connection()
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        release_connection(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Schema DDL — 11 tables
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_TABLES = """
-- ============================================================
-- GEX Domain (4 tables)
-- ============================================================

-- GEXMetrix latest snapshot summary (17 columns)
CREATE TABLE IF NOT EXISTS gex_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    timestamp       DATETIME NOT NULL,
    filename        TEXT NOT NULL,
    net_gex         REAL,
    call_gex        REAL,
    put_gex         REAL,
    zero_gamma_level REAL,
    call_wall       REAL,
    put_wall        REAL,
    spot_price      REAL,
    total_gamma     REAL,
    file_size       INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    quality_score   REAL,
    data_lag_seconds INTEGER,
    oi_coverage_pct REAL,
    is_mock         BOOLEAN DEFAULT 0,
    mock_reason     TEXT
);
CREATE INDEX IF NOT EXISTS idx_gex_snapshots_sym_ts
    ON gex_snapshots (symbol, timestamp DESC);

-- Per-strike real GEX/OI distribution (12 columns)
CREATE TABLE IF NOT EXISTS gex_strikes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    timestamp   DATETIME NOT NULL,
    strike      REAL NOT NULL,
    call_gex    REAL NOT NULL DEFAULT 0,
    put_gex     REAL NOT NULL DEFAULT 0,
    call_oi     INTEGER NOT NULL DEFAULT 0,
    put_oi      INTEGER NOT NULL DEFAULT 0,
    call_vol    INTEGER NOT NULL DEFAULT 0,
    put_vol     INTEGER NOT NULL DEFAULT 0,
    net_gex     REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES gex_snapshots(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_gex_strikes_sym_ts
    ON gex_strikes (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gex_strikes_snap
    ON gex_strikes (snapshot_id);

-- SqueezeMetrics 90-day daily history (8 columns)
CREATE TABLE IF NOT EXISTS gex_history (
    timestamp          DATETIME PRIMARY KEY,
    gex_local          REAL NOT NULL,
    gex_calibrated     REAL,
    alpha_factor       REAL,
    put_wall_level     REAL,
    flip_zone_lower    REAL,
    flip_zone_upper    REAL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alpha factor history (9 columns)
CREATE TABLE IF NOT EXISTS alpha_history (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          DATETIME NOT NULL,
    symbol             TEXT NOT NULL DEFAULT 'SPX',
    alpha_raw          REAL,
    alpha_ewm_20d      REAL,
    alpha_ewm_60d      REAL,
    gex_metrix_net     REAL,
    gex_squeeze_net    REAL,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alpha_history_ts
    ON alpha_history (timestamp DESC);

-- ============================================================
-- Other Dimension Domain (3 tables)
-- ============================================================

-- VIX term structure analysis (9 columns)
CREATE TABLE IF NOT EXISTS vix_analysis (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    vix_spot              REAL,
    vx1                   REAL,
    vx2                   REAL,
    term_structure_ratio  REAL,
    term_structure_state  TEXT,
    panic_premium         REAL,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_mock               BOOLEAN DEFAULT 0,
    mock_reason           TEXT
);

-- VIX term structure daily history (date PK, from FRED VIXCLS + VXVCLS)
CREATE TABLE IF NOT EXISTS vix_term_structure (
    date                    DATE PRIMARY KEY,
    vix_spot                REAL,
    vx_3m_proxy             REAL,  -- VXVCLS (CBOE 3M VIX index) as long-end proxy
    term_structure_ratio    REAL,  -- (vx_3m_proxy / vix_spot - 1) * 100, positive=contango
    term_structure_state    TEXT,  -- contango | backwardation | flat
    panic_premium           REAL,  -- vix_spot - vx_3m_proxy (long-term volatility premium)
    regime                  TEXT,  -- low (<15) | normal (15-25) | elevated (25-35) | panic (>35)
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vix_ts_date ON vix_term_structure(date DESC);

-- Dark pool intraday snapshot history (no PK constraint — multi-row per day, per cycle)
CREATE TABLE IF NOT EXISTS dark_pool_history (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    DATE NOT NULL,
    timestamp               TEXT NOT NULL,
    dix_value               REAL,
    gex_value               REAL,    -- SqueezeMetrics GEX column from CSV
    spx_price               REAL,    -- SqueezeMetrics price column from CSV
    chartexchange_short_ratio REAL,
    source                  TEXT,    -- squeezemetrics | chart-exchange | mock
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_darkpool_hist_date ON dark_pool_history(date DESC);
CREATE INDEX IF NOT EXISTS idx_darkpool_hist_ts ON dark_pool_history(timestamp DESC);

-- Dark pool / DIX metrics (18 columns)
CREATE TABLE IF NOT EXISTS dark_pool_metrics (
    date                       DATE PRIMARY KEY,
    dix_value                  REAL,
    chartexchange_short_ratio  REAL,
    stockgrid_20d_slope        REAL,
    stockgrid_60d_slope        REAL,
    stockgrid_divergence       BOOLEAN,
    dbmf_ma5_recovery          BOOLEAN,
    dix_signal                 BOOLEAN,
    short_ratio_signal         BOOLEAN,
    stockgrid_signal           BOOLEAN,
    aggregated_signal          BOOLEAN,
    v_net                      REAL,
    ema_fast_5                 REAL,
    ema_slow_20                REAL,
    zero_cross_signal          TEXT,
    momentum_reversal_signal   TEXT,
    created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_mock                    BOOLEAN DEFAULT 0,
    mock_reason                TEXT
);

-- Options chain + Greeks (computed via py_vollib Black-Scholes, fed by yfinance)
-- Per-strike detail stored in options_greeks_strikes (1:N)
CREATE TABLE IF NOT EXISTS options_greeks (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                TEXT NOT NULL,
    timestamp             TEXT NOT NULL,
    spot_price            REAL,
    expiry                TEXT,
    days_to_expiry        INTEGER,
    atm_strike            REAL,
    atm_iv                REAL,
    atm_delta_call        REAL,
    atm_delta_put         REAL,
    atm_gamma             REAL,
    atm_vega              REAL,
    atm_theta             REAL,
    risk_free_rate        REAL,
    calls_count           INTEGER,
    puts_count            INTEGER,
    source                TEXT DEFAULT 'yfinance',
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS options_greeks_strikes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id           INTEGER NOT NULL,
    strike                REAL NOT NULL,
    call_delta            REAL,
    put_delta             REAL,
    gamma                 REAL,
    vega                  REAL,
    theta                 REAL,
    iv                    REAL,
    call_oi               INTEGER,
    put_oi                INTEGER,
    FOREIGN KEY (snapshot_id) REFERENCES options_greeks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_options_greeks_symbol_ts
    ON options_greeks (symbol, timestamp DESC);

-- Crypto derivatives (10 columns)
CREATE TABLE IF NOT EXISTS crypto_derivatives (
    timestamp          DATETIME PRIMARY KEY,
    btc_funding_rate   REAL NOT NULL,
    btc_oi             REAL,
    oi_change_1h       REAL,
    liquidation_spike  BOOLEAN,
    cryptoquant_elr    REAL,
    funding_anomaly    BOOLEAN,
    oi_crash           BOOLEAN,
    leverage_cleanup   BOOLEAN,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_mock            BOOLEAN DEFAULT 0,
    mock_reason        TEXT,
    btc_price          REAL,
    btc_24h_change     REAL,
    btc_volume         REAL,
    eth_price          REAL,
    eth_24h_change     REAL
);

-- ============================================================
-- Signal & Audit Domain (3 tables)
-- ============================================================

-- Resonance signal alerts (12 columns)
CREATE TABLE IF NOT EXISTS signal_alerts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_time            DATETIME NOT NULL,
    total_score             REAL NOT NULL,
    gex_score               REAL,
    vix_score               REAL,
    crypto_score            REAL,
    darkpool_score          REAL,
    alert_level             TEXT NOT NULL,
    hawkes_branching_ratio  REAL,
    details                 TEXT,
    acknowledged            BOOLEAN DEFAULT 0,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    outcome                 TEXT DEFAULT NULL,
    forward_return          REAL DEFAULT NULL,
    outcome_checked_at      TEXT DEFAULT NULL,
    mock_sources            TEXT DEFAULT NULL,
    mock_count              INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_signal_alerts_level
    ON signal_alerts (alert_level, trigger_time DESC);
-- FIX-37: Bayesian weight update and outcome tracker both scan this
-- table ordered by outcome status (NULL → unchecked, otherwise
-- pending/replay review). Without an index each query is a full scan.
CREATE INDEX IF NOT EXISTS idx_signal_alerts_outcome
    ON signal_alerts (outcome, outcome_checked_at DESC);

-- Data validation audit log (14 columns)
CREATE TABLE IF NOT EXISTS validation_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    source          TEXT NOT NULL,
    symbol          TEXT,
    check_type      TEXT NOT NULL,
    check_name      TEXT NOT NULL,
    passed          BOOLEAN NOT NULL,
    input_value     TEXT,
    expected_range  TEXT,
    severity        TEXT DEFAULT 'INFO',
    message         TEXT,
    raw_data_hash   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_validation_audit_ts
    ON validation_audit_log (timestamp DESC, source);

-- Gateway snapshots (10 columns)
CREATE TABLE IF NOT EXISTS gateway_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    source          TEXT NOT NULL,
    payload_hash    TEXT,
    payload_size    INTEGER,
    layer1_output   TEXT,
    layer2_output   TEXT,
    status          TEXT DEFAULT 'OK',
    error_message   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gateway_snapshots_ts
    ON gateway_snapshots (timestamp DESC, source);

-- ============================================================
-- System table
-- ============================================================

-- System configuration (key-value store)
CREATE TABLE IF NOT EXISTS system_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# Schema DDL — 5 views
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_VIEWS = """
-- View 1: Latest GEX snapshot per symbol
CREATE VIEW IF NOT EXISTS v_latest_gex_snapshot AS
SELECT
    gs.id,
    gs.symbol,
    gs.timestamp,
    gs.filename,
    gs.net_gex,
    gs.call_gex,
    gs.put_gex,
    gs.zero_gamma_level,
    gs.call_wall,
    gs.put_wall,
    gs.spot_price,
    gs.total_gamma,
    gs.quality_score,
    gs.data_lag_seconds,
    gs.oi_coverage_pct,
    gs.created_at
FROM gex_snapshots gs
INNER JOIN (
    SELECT symbol, MAX(timestamp) AS max_ts
    FROM gex_snapshots
    GROUP BY symbol
) latest ON gs.symbol = latest.symbol AND gs.timestamp = latest.max_ts;

-- View 2: Signal summary with counts per level
CREATE VIEW IF NOT EXISTS v_signal_summary AS
SELECT
    alert_level,
    COUNT(*) AS total_count,
    SUM(CASE WHEN acknowledged = 1 THEN 1 ELSE 0 END) AS acknowledged_count,
    AVG(total_score) AS avg_score,
    MAX(total_score) AS max_score,
    MIN(trigger_time) AS first_trigger,
    MAX(trigger_time) AS last_trigger
FROM signal_alerts
GROUP BY alert_level;

-- View 3: Data source health / freshness
CREATE VIEW IF NOT EXISTS v_source_health AS
SELECT
    'gex_snapshots' AS source,
    MAX(timestamp) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
FROM gex_snapshots
UNION ALL
SELECT
    'vix_analysis' AS source,
    MAX(timestamp) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
FROM vix_analysis
UNION ALL
SELECT
    'vix_term_structure' AS source,
    MAX(date) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(date))) * 24 * 60 AS REAL) AS age_minutes
FROM vix_term_structure
UNION ALL
SELECT
    'dark_pool_metrics' AS source,
    MAX(date) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(date))) * 24 * 60 AS REAL) AS age_minutes
FROM dark_pool_metrics
UNION ALL
SELECT
    'dark_pool_history' AS source,
    MAX(timestamp) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
FROM dark_pool_history
UNION ALL
SELECT
    'crypto_derivatives' AS source,
    MAX(timestamp) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
FROM crypto_derivatives
UNION ALL
SELECT
    'options_greeks' AS source,
    MAX(timestamp) AS last_data_ts,
    COUNT(*) AS total_rows,
    CAST((julianday('now') - julianday(MAX(timestamp))) * 24 * 60 AS REAL) AS age_minutes
FROM options_greeks;

-- View 4: Daily dark pool aggregation
CREATE VIEW IF NOT EXISTS v_daily_darkpool AS
SELECT
    date,
    dix_value,
    v_net,
    ema_fast_5,
    ema_slow_20,
    aggregated_signal,
    zero_cross_signal,
    momentum_reversal_signal,
    chartexchange_short_ratio,
    created_at,
    updated_at
FROM dark_pool_metrics
ORDER BY date DESC;

-- View 5: Resonance dashboard — latest scores with dimension breakdown
CREATE VIEW IF NOT EXISTS v_resonance_dashboard AS
SELECT
    sa.id,
    sa.trigger_time,
    sa.total_score,
    sa.gex_score,
    sa.vix_score,
    sa.crypto_score,
    sa.darkpool_score,
    sa.alert_level,
    sa.hawkes_branching_ratio,
    sa.acknowledged,
    gs.symbol AS gex_symbol,
    gs.net_gex AS latest_net_gex,
    gs.spot_price AS latest_spot_price,
    va.vix_spot AS latest_vix_spot,
    va.term_structure_state AS latest_vix_state
FROM signal_alerts sa
LEFT JOIN v_latest_gex_snapshot gs ON gs.symbol = 'SPX'
LEFT JOIN (
    SELECT * FROM vix_analysis
    WHERE timestamp = (SELECT MAX(timestamp) FROM vix_analysis)
) va ON 1=1
ORDER BY sa.trigger_time DESC;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Default system_config seed data
# ─────────────────────────────────────────────────────────────────────────────

SEED_CONFIG = """
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
    ('alpha_factor', '1.0', 'GEX calibration coefficient (GEXMetrix vs SqueezeMetrics)'),
    ('gex_threshold', '35000000', 'GEX threshold value (35M)'),
    ('alert_level_3_min', '75', 'Minimum score for LEVEL_3 alert (normalized 0-100)');
"""


# ─────────────────────────────────────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Initialize database: create all tables, views, and seed data.

    Called on application startup. Safe to call multiple times (uses IF NOT EXISTS).
    """
    db_path = settings.db_absolute_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing database at: {db_path}")

    conn = await aiosqlite.connect(str(db_path))
    try:
        # Enable WAL mode
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA foreign_keys=ON")

        # Create all tables
        await conn.executescript(SCHEMA_TABLES)

        # Create all views
        await conn.executescript(SCHEMA_VIEWS)

        # Seed default config
        await conn.executescript(SEED_CONFIG)

        # Idempotent migrations for mock tracking columns
        alter_statements = [
            # Mock tracking columns (FIX-01)
            "ALTER TABLE gex_snapshots ADD COLUMN is_mock BOOLEAN DEFAULT 0",
            "ALTER TABLE gex_snapshots ADD COLUMN mock_reason TEXT",
            "ALTER TABLE vix_analysis ADD COLUMN is_mock BOOLEAN DEFAULT 0",
            "ALTER TABLE vix_analysis ADD COLUMN mock_reason TEXT",
            "ALTER TABLE crypto_derivatives ADD COLUMN is_mock BOOLEAN DEFAULT 0",
            "ALTER TABLE crypto_derivatives ADD COLUMN mock_reason TEXT",
            "ALTER TABLE dark_pool_metrics ADD COLUMN is_mock BOOLEAN DEFAULT 0",
            "ALTER TABLE dark_pool_metrics ADD COLUMN mock_reason TEXT",
            "ALTER TABLE signal_alerts ADD COLUMN mock_sources TEXT DEFAULT NULL",
            "ALTER TABLE signal_alerts ADD COLUMN mock_count INTEGER DEFAULT 0",
            # Outcome tracking columns (legacy)
            "ALTER TABLE signal_alerts ADD COLUMN outcome TEXT DEFAULT NULL",
            "ALTER TABLE signal_alerts ADD COLUMN forward_return REAL DEFAULT NULL",
            "ALTER TABLE signal_alerts ADD COLUMN outcome_checked_at TEXT DEFAULT NULL",
            # CoinGecko enrichment columns
            "ALTER TABLE crypto_derivatives ADD COLUMN btc_price REAL",
            "ALTER TABLE crypto_derivatives ADD COLUMN btc_24h_change REAL",
            "ALTER TABLE crypto_derivatives ADD COLUMN btc_volume REAL",
            "ALTER TABLE crypto_derivatives ADD COLUMN eth_price REAL",
            "ALTER TABLE crypto_derivatives ADD COLUMN eth_24h_change REAL",
        ]
        for stmt in alter_statements:
            try:
                await conn.execute(stmt)
            except Exception:
                pass  # Column already exists

        await conn.commit()
        logger.info("Database schema initialized successfully (11 tables + 5 views)")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await conn.close()


async def close_db() -> None:
    """Close all pooled connections on application shutdown."""
    global _connections
    for conn in _connections:
        try:
            await conn.close()
        except Exception:
            pass
    _connections.clear()
    logger.info("Database connections closed")
