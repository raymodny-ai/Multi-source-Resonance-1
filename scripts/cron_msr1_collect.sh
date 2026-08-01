#!/usr/bin/env bash
# MSR-1 Daily Collect wrapper (no LLM, 0 依赖)
# 为 cron 22:00 ET 自动跑 collect-manual — 调用现有后端 (port 8525)
# 替换旧的 cron_msr_collect.sh (那个跑旧 MSR Multi-source-Resonance, 端口 8524)
set -uo pipefail

WS="/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1"
NOTIFY="${WS}/.cron_tg_notify.sh"
LOG_DIR="${WS}/logs"
mkdir -p "${LOG_DIR}"

cd "${WS}"

# 拿 MSR_ADMIN_PASSWORD (FIX-05, 从 .env 或 fallback 默认 admin)
ADMIN_PW="admin"
if [ -f "./.env" ]; then
  ADMIN_PW=$(grep '^MSR_ADMIN_PASSWORD=' ./.env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
if [ -z "${ADMIN_PW}" ]; then
  ADMIN_PW="admin"
fi

ET_DATE=$(TZ='America/New_York' date +%F)
LOG_FILE="${LOG_DIR}/msr1_cron_${ET_DATE}.log"
BACKEND_URL="http://localhost:8525"

# 拿 JWT token
TOKEN=$(curl -fsS --max-time 10 \
  -X POST "${BACKEND_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PW}\"}" \
  | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('access_token',''))" 2>/dev/null)

if [ -z "${TOKEN}" ]; then
  "${NOTIFY}" "❌ <b>MSR-1 每日采集失败</b>
无法登录 backend (port 8525)
可能 backend 没跑 · 美东 ${ET_DATE}"
  exit 1
fi

# 触发 collect-manual
START_TS=$(date +%s)
RESP=$(curl -fsS --max-time 300 \
  -X POST "${BACKEND_URL}/api/system/collect-manual" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" 2>&1)
EXIT_CODE=$?
END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

echo "RESP=${RESP}" > "${LOG_FILE}"
echo "ELAPSED=${ELAPSED}s" >> "${LOG_FILE}"

if [ "${EXIT_CODE}" -ne 0 ] || [ -z "${RESP}" ]; then
  "${NOTIFY}" "⚠️ <b>MSR-1 每日采集异常</b>
exit=${EXIT_CODE} · 耗时 ${ELAPSED}s · 美东 ${ET_DATE}
响应: <code>${RESP:0:300}</code>
日志: ${LOG_FILE}"
  exit "${EXIT_CODE:-1}"
fi

# 解析 JSON
OK=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('ok', False))" 2>/dev/null)
SUCCESS=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('success_count', '?'))" 2>/dev/null)
ERRORS=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error_count', '?'))" 2>/dev/null)

if [ "${OK}" = "True" ]; then
  "${NOTIFY}" "✅ <b>MSR-1 每日采集完成</b>
${SUCCESS} 成功 / ${ERRORS} 失败 · 耗时 ${ELAPSED}s
美东 ${ET_DATE}
前端: http://10.18.1.251:5173/
后端: ${BACKEND_URL}/api/health"
  exit 0
else
  "${NOTIFY}" "⚠️ <b>MSR-1 采集部分失败</b>
${SUCCESS} 成功 / ${ERRORS} 失败 · 耗时 ${ELAPSED}s
美东 ${ET_DATE}
响应: <code>${RESP:0:400}</code>"
  exit 1
fi