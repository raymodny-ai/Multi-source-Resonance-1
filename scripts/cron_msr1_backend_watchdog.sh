#!/usr/bin/env bash
# MSR-1 Backend Watchdog — 每分钟巡检 backend (port 8525)
# 若 backend 死了: 自动 nohup 重启 + TG 推 "restarted"
# 状态变更才推 TG (避免刷屏)
# 类似 PIT-Docker Watchdog 模式 (every 60s)
set -uo pipefail

WS="/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1"
NOTIFY="${WS}/.cron_tg_notify.sh"
LOCK="/tmp/msr1_backend.lock"
BACKEND_PORT=8525
HEALTH_URL="http://localhost:${BACKEND_PORT}/api/health"

# 现有 PID?
EXISTING_PIDS=$(ss -tlnp 2>/dev/null | grep ":${BACKEND_PORT} " | grep -oE 'pid=[0-9]+' | grep -oE '[0-9]+' | sort -u)

# 健康?
HEALTHY=false
if [ -n "${EXISTING_PIDS}" ]; then
  for PID in ${EXISTING_PIDS}; do
    CODE=$(curl -fsS --max-time 3 -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null || echo "000")
    if [ "${CODE}" = "200" ]; then
      HEALTHY=true
      break
    fi
  done
fi

if [ "${HEALTHY}" = "true" ]; then
  # 健康: 清掉 lock (如果有)
  [ -f "${LOCK}" ] && rm -f "${LOCK}" && {
    "${NOTIFY}" "✅ <b>MSR-1 backend 恢复</b>
port ${BACKEND_PORT} 健康 · $(date '+%F %T %Z')"
  }
  exit 0
fi

# 不健康: 看 lock 是否已存在 (避免 1 分钟内多次重启 + 刷屏)
if [ -f "${LOCK}" ]; then
  # 已经在处理中, 跳过
  exit 0
fi

# 第一次发现挂了: lock + 重启 + TG 推
echo "$(date +%s)" > "${LOCK}"

# 杀残留进程
pkill -f 'backend.main' 2>/dev/null || true
sleep 2

# 重启
# 注意: 不要用 `python -m backend.main` (会走 __main__ 分支 reload=True, 启 spawn 子进程, 日志被 multiprocessing pipe 吞掉)
# 直接 uvicorn backend.main:app 走 app import 路径, 单进程, --reload=False
cd "${WS}"
PORT="${BACKEND_PORT}" nohup .venv/bin/uvicorn backend.main:app \
  --host 0.0.0.0 --port "${BACKEND_PORT}" --no-access-log \
  > "${WS}/logs/backend.log" 2>&1 < /dev/null &
NEW_PID=$!
sleep 6

# 验证
CODE=$(curl -fsS --max-time 5 -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null || echo "000")
if [ "${CODE}" = "200" ]; then
  "${NOTIFY}" "🔧 <b>MSR-1 backend 自动重启</b>
port ${BACKEND_PORT} · new PID ${NEW_PID} · $(date '+%F %T %Z')
详情: 前次 watchdog 检测到不健康"
  rm -f "${LOCK}"
  exit 0
else
  "${NOTIFY}" "❌ <b>MSR-1 backend 重启失败</b>
port ${BACKEND_PORT} · PID ${NEW_PID} · HTTP ${CODE}
$(date '+%F %T %Z') · 需 Owner 手动检查"
  # 保留 lock, 下次再试
  exit 1
fi