#!/usr/bin/env bash
# MSR-1 Open-Bell Collect — 美东 09:35 早盘开盘后采集
# 与 22:00 同一 wrapper, 但 TG 标签标 "Open-Bell"
set -uo pipefail

WS="/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1"
NOTIFY="${WS}/.cron_tg_notify.sh"
LOG_DIR="${WS}/logs"
mkdir -p "${LOG_DIR}"

cd "${WS}"
ADMIN_PW="admin"
if [ -f "./.env" ]; then
  ADMIN_PW=$(grep '^ADMIN_PASSWORD=' ./.env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
[ -z "${ADMIN_PW}" ] && ADMIN_PW="admin"

ET_DATE=$(TZ='America/New_York' date +%F)
LOG_FILE="${LOG_DIR}/msr1_open_${ET_DATE}.log"
BACKEND_URL="http://localhost:8525"

# Login → JWT
LOGIN_RESP=$(curl -fsS --max-time 10 \
  -X POST "${BACKEND_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PW}\"}" 2>/dev/null)

TOKEN=$(echo "${LOGIN_RESP}" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('access_token',''))" 2>/dev/null)

if [ -z "${TOKEN}" ]; then
  "${NOTIFY}" "❌ <b>MSR-1 早盘采集失败</b>
backend 登录失败 · 美东 ${ET_DATE} 09:35"
  exit 1
fi

START_TS=$(date +%s)
RESP=$(curl -fsS --max-time 300 \
  -X POST "${BACKEND_URL}/api/system/collect-manual" \
  -H "Authorization: Bearer ${TOKEN}" 2>&1)
EXIT_CODE=$?
ELAPSED=$(($(date +%s) - START_TS))

echo "RESP=${RESP}" > "${LOG_FILE}"
echo "ELAPSED=${ELAPSED}s" >> "${LOG_FILE}"

if [ "${EXIT_CODE}" -ne 0 ]; then
  "${NOTIFY}" "⚠️ <b>MSR-1 早盘采集异常</b>
exit=${EXIT_CODE} · ${ELAPSED}s · 美东 ${ET_DATE} 09:35"
  exit "${EXIT_CODE}"
fi

OK=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('ok', False))" 2>/dev/null)
SUCCESS=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('success_count', '?'))" 2>/dev/null)
ERRORS=$(echo "${RESP}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error_count', '?'))" 2>/dev/null)

"${NOTIFY}" "🌅 <b>MSR-1 早盘采集完成</b>
${SUCCESS} 成功 / ${ERRORS} 失败 · ${ELAPSED}s
美东 ${ET_DATE} 09:35 (开盘后 5min)"

exit 0