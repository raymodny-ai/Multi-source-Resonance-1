#!/usr/bin/env bash
# MSR-1 手动触发一次完整 pipeline cycle (带 JWT)
# 用法: bash scripts/manual_collect.sh
# 说明: FIX-05 后 collect-manual 需 JWT。本脚本从 .env 读 MSR_ADMIN_PASSWORD 登录后触发。
# 注: 若 pipeline 正处在周期 sleep (每 15min 自动跑, 期间 is_running=True) 会返回 409,
#     此时可 --force-wait 等 sleep 结束, 或稍后重试。
set -uo pipefail

WS="/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1"
cd "${WS}"
BACKEND_URL="http://localhost:8525"

# 从 .env 读 FIX-05 密码
ADMIN_PW=$(grep '^MSR_ADMIN_PASSWORD=' ./.env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
[ -z "${ADMIN_PW}" ] && { echo "❌ .env 无 MSR_ADMIN_PASSWORD"; exit 1; }

# 登录拿 token
TOKEN=$(curl -fsS --max-time 10 -X POST "${BACKEND_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PW}\"}" 2>/dev/null \
  | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('access_token',''))" 2>/dev/null)
[ -z "${TOKEN}" ] && { echo "❌ 登录失败"; exit 1; }

# 触发采集 (最多等 300s)
echo "⏳ 触发 collect-manual ..."
RESP=$(curl -sS --max-time 300 -X POST "${BACKEND_URL}/api/system/collect-manual" \
  -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" 2>&1)
CODE=$?

if [ "${CODE}" -eq 0 ] && echo "${RESP}" | grep -q "already running"; then
  echo "⚠️ 409: pipeline 正在周期运行/sleep (每15min自动跑), 无法同时手动触发。"
  echo "   下次自动 cycle 会自行运行; 或等其结束后重跑本脚本。"
  exit 2
fi

if [ "${CODE}" -ne 0 ]; then
  echo "❌ 请求失败 exit=${CODE}: ${RESP:0:300}"
  exit 1
fi

echo "${RESP}" | python3 -c "
import json,sys
d=json.loads(sys.stdin.read())
print('ok:', d.get('ok'), '| elapsed:', d.get('total_elapsed_sec'), 's')
print('success:', d.get('success_count'), '| error:', d.get('error_count'), '| mock:', d.get('mock_count'))
for s in (d.get('sources') or []):
    n=s.get('source', s); print(f'  {n}: ok={s.get(\"ok\")} err={str(s.get(\"error\") or \"\")[:40]}')
"
