#!/usr/bin/env bash
# MSR-1 Weekly Backfill — 美东 周日 18:00 跑 gex_history 一年回填
# 维护: SqueezeMetrics CSV 是 ~15 年历史, 365 天覆盖近一年
set -uo pipefail

WS="/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1"
NOTIFY="${WS}/.cron_tg_notify.sh"
LOG_DIR="${WS}/logs"
mkdir -p "${LOG_DIR}"

cd "${WS}"

ET_DATE=$(TZ='America/New_York' date +%F)
LOG_FILE="${LOG_DIR}/msr1_backfill_${ET_DATE}.log"

# 跑 365 天 backfill (近一年)
START_TS=$(date +%s)
if .venv/bin/python scripts/backfill_gex_history.py --days 365 > "${LOG_FILE}" 2>&1; then
  ELAPSED=$(($(date +%s) - START_TS))
  # 抽 INSERT 行数
  ROWS=$(grep -oE 'INSERT.*rows[^0-9]*[0-9]+' "${LOG_FILE}" | tail -1 | grep -oE '[0-9]+$')
  ROWS=${ROWS:-"?"}
  "${NOTIFY}" "📊 <b>MSR-1 weekly backfill 完成</b>
365 天 gex_history · ${ROWS} 行入库
${ELAPSED}s · 美东 ${ET_DATE}"
  exit 0
else
  "${NOTIFY}" "❌ <b>MSR-1 weekly backfill 失败</b>
日志: ${LOG_FILE}"
  exit 1
fi
