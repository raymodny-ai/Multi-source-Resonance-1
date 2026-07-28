#!/usr/bin/env bash
# ~/.cron_tg_notify.sh — 统一 TG Bot API 推送 helper
# 给所有 OpenClaw cron wrapper 调用,避免每个 cron 都 inline token
# Token 从 OpenClaw config 自动读; 调用: tg_notify "<text>" [chat_id_default=850492903]
set -euo pipefail

TG_CHAT_ID="${2:-850492903}"
TEXT="$1"

# 从 OpenClaw config 拿 bot token (只读, 不污染环境)
TOKEN="$(python3 -c '
import json, sys
p = "/vol1/@apphome/trim.openclaw/data/home/.openclaw/openclaw.json"
try:
    print(json.load(open(p))["channels"]["telegram"]["botToken"])
except Exception as e:
    sys.stderr.write(f"TG token read failed: {e}\n")
    sys.exit(1)
')"

# 支持长消息 (TG 限制 4096 字符,超出截断)
if [ "${#TEXT}" -gt 4000 ]; then
  TEXT="${TEXT:0:3950}…(truncated)"
fi

# 调用 Bot API,失败不抛错 (cron 已经记 lastRunStatus)
curl -fsS --max-time 15 \
  -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TG_CHAT_ID}" \
  --data-urlencode "text=${TEXT}" \
  --data-urlencode "parse_mode=HTML" \
  --data-urlencode "disable_web_page_preview=true" \
  > /dev/null || echo "[$(date '+%T')] TG push failed (ignored)" >&2
