#!/usr/bin/env bash
# =============================================================================
# Database Backup Script for Multi-source Resonance Monitor
#
# Features:
#   - Daily incremental backup (changes since last full backup)
#   - Weekly full backup (complete database copy)
#   - Retention policy: 30 days
#
# Usage:
#   ./db_backup.sh [full|incremental|auto]
#   auto: full on Monday, incremental on other days
#
# Cron setup (daily at 3:00 AM):
#   0 3 * * * /path/to/scripts/db_backup.sh auto >> /var/log/resonance_backup.log 2>&1
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="${PROJECT_ROOT}/data/resonance.db"
BACKUP_DIR="${PROJECT_ROOT}/data/backups"
RETENTION_DAYS=30
LOG_PREFIX="[db_backup]"

# ── Functions ────────────────────────────────────────────────────────────────

log_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO: $1"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $1" >&2
}

log_warn() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} WARN: $1"
}

# Check prerequisites
check_prerequisites() {
    if [ ! -f "$DB_PATH" ]; then
        log_error "Database file not found: $DB_PATH"
        exit 1
    fi

    if ! command -v sqlite3 &> /dev/null; then
        log_warn "sqlite3 not found, skipping integrity check"
    fi

    mkdir -p "$BACKUP_DIR"
}

# Verify database integrity before backup
verify_integrity() {
    if command -v sqlite3 &> /dev/null; then
        log_info "Verifying database integrity..."
        local result
        result=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)
        if [ "$result" != "ok" ]; then
            log_error "Database integrity check failed: $result"
            log_error "Aborting backup. See docs/troubleshooting.md for recovery."
            exit 1
        fi
        log_info "Database integrity check passed"
    fi
}

# Full backup: complete database copy with WAL checkpoint
do_full_backup() {
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/resonance_full_${timestamp}.db"
    local backup_wal="${BACKUP_DIR}/resonance_full_${timestamp}.db-wal"

    log_info "Starting FULL backup..."

    # Force WAL checkpoint to merge pending changes
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
    fi

    # Use SQLite's backup command for consistency
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" ".backup '${backup_file}'"
        log_info "Full backup created: ${backup_file}"
    else
        # Fallback: file copy
        cp "$DB_PATH" "$backup_file"
        [ -f "${DB_PATH}-wal" ] && cp "${DB_PATH}-wal" "$backup_wal" || true
        [ -f "${DB_PATH}-shm" ] && cp "${DB_PATH}-shm" "${BACKUP_DIR}/resonance_full_${timestamp}.db-shm" || true
        log_info "Full backup created (file copy): ${backup_file}"
    fi

    # Compress backup
    if command -v gzip &> /dev/null; then
        gzip "$backup_file"
        log_info "Backup compressed: ${backup_file}.gz"
        # Record backup metadata
        echo "${timestamp}|full|$(stat -f%z "${backup_file}.gz" 2>/dev/null || stat -c%s "${backup_file}.gz" 2>/dev/null || echo 'unknown')" \
            >> "${BACKUP_DIR}/backup_manifest.txt"
    else
        echo "${timestamp}|full|$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo 'unknown')" \
            >> "${BACKUP_DIR}/backup_manifest.txt"
    fi

    log_info "Full backup completed successfully"
}

# Incremental backup: dump changed tables since last full backup
do_incremental_backup() {
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/resonance_incr_${timestamp}.db"

    log_info "Starting INCREMENTAL backup..."

    # Find last full backup
    local last_full
    last_full=$(ls -t "${BACKUP_DIR}"/resonance_full_*.db* 2>/dev/null | head -1)

    if [ -z "$last_full" ]; then
        log_warn "No full backup found, performing full backup instead"
        do_full_backup
        return
    fi

    # Create incremental backup with changed data
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" <<EOF
ATTACH '${last_full}' AS full_backup;

-- Create incremental database
ATTACH '${backup_file}' AS incr;

-- Export tables that may have changed since last full backup
-- signal_alerts: new signals
CREATE TABLE incr.signal_alerts AS
SELECT * FROM signal_alerts
WHERE trigger_time > (SELECT COALESCE(MAX(trigger_time), '1970-01-01') FROM full_backup.signal_alerts);

-- gex_snapshots: new snapshots
CREATE TABLE incr.gex_snapshots AS
SELECT * FROM gex_snapshots
WHERE timestamp > (SELECT COALESCE(MAX(timestamp), '1970-01-01') FROM full_backup.gex_snapshots);

-- gex_strikes: new strikes
CREATE TABLE incr.gex_strikes AS
SELECT * FROM gex_strikes
WHERE timestamp > (SELECT COALESCE(MAX(timestamp), '1970-01-01') FROM full_backup.gex_strikes);

-- vix_analysis: new entries
CREATE TABLE incr.vix_analysis AS
SELECT * FROM vix_analysis
WHERE timestamp > (SELECT COALESCE(MAX(timestamp), '1970-01-01') FROM full_backup.vix_analysis);

-- dark_pool_metrics: new entries
CREATE TABLE incr.dark_pool_metrics AS
SELECT * FROM dark_pool_metrics
WHERE date > (SELECT COALESCE(MAX(date), '1970-01-01') FROM full_backup.dark_pool_metrics);

-- crypto_derivatives: new entries
CREATE TABLE incr.crypto_derivatives AS
SELECT * FROM crypto_derivatives
WHERE timestamp > (SELECT COALESCE(MAX(timestamp), '1970-01-01') FROM full_backup.crypto_derivatives);

-- system_config: full copy (small table)
CREATE TABLE incr.system_config AS
SELECT * FROM system_config;

DETACH full_backup;
DETACH incr;
EOF
        log_info "Incremental backup created: ${backup_file}"
    else
        log_warn "sqlite3 not available, falling back to full backup"
        do_full_backup
        return
    fi

    # Compress
    if command -v gzip &> /dev/null; then
        gzip "$backup_file"
        log_info "Incremental backup compressed: ${backup_file}.gz"
    fi

    # Record metadata
    local size
    size=$(stat -f%z "${backup_file}.gz" 2>/dev/null || stat -c%s "${backup_file}.gz" 2>/dev/null || echo 'unknown')
    echo "${timestamp}|incremental|${size}" >> "${BACKUP_DIR}/backup_manifest.txt"

    log_info "Incremental backup completed successfully"
}

# Cleanup old backups based on retention policy
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    local count=0

    # Remove old full backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        count=$((count + 1))
    done < <(find "$BACKUP_DIR" -name "resonance_full_*.db*" -mtime +${RETENTION_DAYS} -print0 2>/dev/null)

    # Remove old incremental backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        count=$((count + 1))
    done < <(find "$BACKUP_DIR" -name "resonance_incr_*.db*" -mtime +${RETENTION_DAYS} -print0 2>/dev/null)

    # Clean up manifest entries for deleted backups
    if [ -f "${BACKUP_DIR}/backup_manifest.txt" ]; then
        local cutoff_date
        cutoff_date=$(date -d "-${RETENTION_DAYS} days" '+%Y%m%d' 2>/dev/null || date -v-${RETENTION_DAYS}d '+%Y%m%d' 2>/dev/null || echo '')
        if [ -n "$cutoff_date" ]; then
            awk -F'|' -v cutoff="$cutoff_date" '$1 >= cutoff' "${BACKUP_DIR}/backup_manifest.txt" \
                > "${BACKUP_DIR}/backup_manifest_tmp.txt" 2>/dev/null || true
            mv "${BACKUP_DIR}/backup_manifest_tmp.txt" "${BACKUP_DIR}/backup_manifest.txt" 2>/dev/null || true
        fi
    fi

    log_info "Cleanup completed: ${count} old backup files removed"
}

# Print backup summary
print_summary() {
    log_info "=== Backup Summary ==="

    local full_count
    full_count=$(find "$BACKUP_DIR" -name "resonance_full_*.db*" 2>/dev/null | wc -l)
    local incr_count
    incr_count=$(find "$BACKUP_DIR" -name "resonance_incr_*.db*" 2>/dev/null | wc -l)
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

    log_info "Full backups: ${full_count}"
    log_info "Incremental backups: ${incr_count}"
    log_info "Total backup size: ${total_size}"
    log_info "Backup directory: ${BACKUP_DIR}"
    log_info "Retention policy: ${RETENTION_DAYS} days"

    # Latest backup info
    local latest
    latest=$(ls -t "${BACKUP_DIR}"/resonance_*.db* 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
        log_info "Latest backup: $(basename "$latest") ($(stat -f%Sm "$latest" 2>/dev/null || stat -c%y "$latest" 2>/dev/null || echo 'unknown'))"
    else
        log_warn "No backups found"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    local mode="${1:-auto}"

    log_info "=== Database Backup Started (mode: ${mode}) ==="

    check_prerequisites
    verify_integrity

    case "$mode" in
        full)
            do_full_backup
            ;;
        incremental|incr)
            do_incremental_backup
            ;;
        auto)
            # Full backup on Monday, incremental on other days
            local day_of_week
            day_of_week=$(date '+%u')  # 1=Monday, 7=Sunday
            if [ "$day_of_week" -eq 1 ]; then
                log_info "Monday detected: performing full backup"
                do_full_backup
            else
                log_info "Performing incremental backup (day ${day_of_week})"
                do_incremental_backup
            fi
            ;;
        *)
            echo "Usage: $0 [full|incremental|auto]"
            echo "  full         - Complete database backup"
            echo "  incremental  - Only changed data since last full backup"
            echo "  auto         - Full on Monday, incremental otherwise (default)"
            exit 1
            ;;
    esac

    cleanup_old_backups
    print_summary

    log_info "=== Database Backup Completed ==="
}

main "$@"
