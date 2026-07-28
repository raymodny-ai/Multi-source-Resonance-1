# 多源共振监控系统 — 故障恢复手册

> 本文档提供常见故障的排查步骤和恢复方案，适用于 v3.1 版本。

---

## 目录

1. [SQLite 数据库损坏恢复](#1-sqlite-数据库损坏恢复)
2. [EventBus 死锁处理](#2-eventbus-死锁处理)
3. [数据源连接失败排查](#3-数据源连接失败排查)
4. [Pipeline 卡住处理](#4-pipeline-卡住处理)
5. [API 服务崩溃恢复](#5-api-服务崩溃恢复)
6. [常见问题 FAQ](#6-常见问题-faq)

---

## 1. SQLite 数据库损坏恢复

### 症状

- API 启动时报错 `database disk image is malformed`
- 查询返回 `IntegrityError`
- 数据库文件大小突然变为 0 或异常增大

### 诊断步骤

```bash
# 1. 检查数据库完整性
sqlite3 data/resonance.db "PRAGMA integrity_check;"

# 2. 检查 WAL 文件状态
ls -la data/resonance.db*
# 正常情况: .db, .db-shm, .db-wal 三个文件

# 3. 检查数据库大小
du -sh data/resonance.db*
```

### 恢复方案

#### 方案 A: WAL 检查点合并（推荐首选）

```bash
# 停止 API 服务
systemctl stop multi-resonance

# 强制 WAL 检查点，合并到主数据库
sqlite3 data/resonance.db "PRAGMA wal_checkpoint(TRUNCATE);"

# 验证完整性
sqlite3 data/resonance.db "PRAGMA integrity_check;"

# 重启服务
systemctl start multi-resonance
```

#### 方案 B: 从备份恢复

```bash
# 查找最近的备份
ls -lt /backup/resonance/

# 恢复全量备份
cp /backup/resonance/resonance_full_20260728.db data/resonance.db

# 应用增量备份（如有）
# 增量备份通过 ATTACH 合并
sqlite3 data/resonance.db <<EOF
ATTACH '/backup/resonance/resonance_incr_20260728.db' AS incr;
INSERT OR REPLACE INTO signal_alerts SELECT * FROM incr.signal_alerts;
INSERT OR REPLACE INTO gex_snapshots SELECT * FROM incr.gex_snapshots;
DETACH incr;
EOF
```

#### 方案 C: 导出数据重建

```bash
# 尝试导出可读取的数据
sqlite3 data/resonance.db ".dump" > data/recovery_dump.sql

# 如果 .dump 失败，逐表导出
for table in gex_snapshots gex_strikes gex_history vix_analysis dark_pool_metrics crypto_derivatives signal_alerts system_config; do
    sqlite3 data/resonance.db ".dump ${table}" > "data/recovery_${table}.sql" 2>/dev/null
done

# 创建新数据库并导入
mv data/resonance.db data/resonance_corrupted.db
python -c "from backend.database import init_db; import asyncio; asyncio.run(init_db())"

# 逐表恢复数据
for f in data/recovery_*.sql; do
    sqlite3 data/resonance.db < "$f" 2>/dev/null
done
```

### 预防措施

- 启用自动备份脚本: `scripts/db_backup.sh`
- 定期执行 `PRAGMA integrity_check`
- 监控数据库大小告警 (>1GB)

---

## 2. EventBus 死锁处理

### 症状

- Pipeline 停止处理新事件
- `eventbus_queue_depth` 持续增长
- 日志中出现 `asyncio` 超时或 `Task was destroyed but it is pending`

### 诊断步骤

```bash
# 检查 EventBus 状态
curl -s http://localhost:8524/api/status | python -m json.tool

# 查看事件历史
curl -s http://localhost:8524/api/metrics | grep eventbus

# 检查进程状态
ps aux | grep resonance
```

### 恢复方案

```bash
# 方案 1: 重启 API 服务（最快）
systemctl restart multi-resonance

# 方案 2: 优雅关闭后重启
# 发送 SIGTERM 让服务完成当前任务
kill -SIGTERM $(pgrep -f "resonance")
sleep 5
systemctl start multi-resonance

# 方案 3: 如果服务无响应
kill -9 $(pgrep -f "resonance")
sleep 2
systemctl start multi-resonance
```

### 根因分析

- 检查 handler 中是否有阻塞操作（同步 I/O）
- 检查是否有循环依赖导致死锁
- 查看 EventBus 统计: `event_bus.get_stats()`

---

## 3. 数据源连接失败排查

### 症状

- `/api/system/source-status` 显示某数据源 `offline`
- 采集失败率 > 20% 触发 Prometheus 告警
- 特定维度评分为 0

### 排查流程

#### 3.1 GEXMetrix API

```bash
# 检查 API Key 配置
grep GEXMETRIX_API_KEY .env

# 测试连通性
curl -v https://api.gexmetrix.com/v1/snapshot/SPY \
  -H "Authorization: Bearer ${GEXMETRX_API_KEY}"

# 常见错误:
# - 401: API Key 过期或无效 → 重新获取 Key
# - 429: 请求频率超限 → 降低采集频率
# - 503: 服务不可用 → 等待或启用 SqueezeMetrics 降级
```

#### 3.2 VIX 数据源 (CBOE)

```bash
# CBOE 免费接口，检查网络连通性
curl -v https://cdn.cboe.com/api/rtd/chart/shorttermbetaadjust.csv

# 如果超时: 检查 DNS 解析和防火墙规则
nslookup cdn.cboe.com
```

#### 3.3 加密衍生品 (Hyperliquid)

```bash
# 测试 Hyperliquid API
curl -X POST https://api.hyperliquid.xyz/info \
  -H "Content-Type: application/json" \
  -d '{"type": "metaAndAssetCtxs"}'

# 降级到 CCData (需要 API Key)
grep CCDATA_API_KEY .env
```

#### 3.4 暗池数据 (AXLFI/DBMF)

```bash
# 检查 AXLFI 连通性
curl -v https://api.axlfi.com/v1/darkpool \
  -H "Authorization: Bearer ${AXLFI_API_KEY}"

# DBMF 均线数据检查
curl -v https://api.dbmf.com/v1/signal
```

### 通用降级策略

系统内置降级链:
- **GEX**: GEXMetrix → SqueezeMetrics (日级数据)
- **Crypto**: Hyperliquid → CCData → 返回空 + 标记 OFFLINE
- **Short Interest**: FINRA → yfinance (估算)

当主数据源不可用时，系统自动切换降级源。

---

## 4. Pipeline 卡住处理

### 症状

- `/api/dashboard/pipeline-metrics` 显示某阶段耗时异常
- `signal_last_generated_timestamp` 超过 5 分钟未更新
- Prometheus 告警 `SignalLatencyHigh` 触发

### 诊断步骤

```bash
# 查看 Pipeline 各阶段耗时
curl -s http://localhost:8524/api/dashboard/pipeline-metrics | python -m json.tool

# 检查当前运行的 Pipeline 实例
ps aux | grep pipeline

# 查看最近日志
journalctl -u multi-resonance --since "10 minutes ago" --no-pager
```

### 恢复方案

```bash
# 1. 重启 Pipeline 进程
systemctl restart multi-resonance

# 2. 如果特定阶段卡住，检查对应数据源
# 阶段 1 (采集): 检查数据源连通性 → 参考第 3 节
# 阶段 2 (校验): 检查数据格式是否异常
# 阶段 3 (计算): 检查 CPU/内存使用
# 阶段 4 (网关): 检查 JSON 序列化是否有异常数据
# 阶段 5 (评分): 检查 scoring.py 权重配置
# 阶段 6 (LLM): 检查 LLM API 连通性

# 3. 手动触发一次采集
curl -X POST http://localhost:8524/api/system/collect-manual
```

### 超时配置

Pipeline 各阶段超时在 `backend/config.py` 中配置:
```python
fetch_timeout_seconds: int = 30  # 采集超时
max_workers: int = 8             # 并发线程数
```

---

## 5. API 服务崩溃恢复

### 症状

- `curl http://localhost:8524/api/health` 无响应
- Prometheus 告警 `ServiceDown` 触发
- 前端页面无法加载

### 快速恢复

```bash
# 检查服务状态
systemctl status multi-resonance

# 查看崩溃日志
journalctl -u multi-resonance -n 50 --no-pager

# 重启服务
systemctl restart multi-resonance

# 验证恢复
curl -s http://localhost:8524/api/health | python -m json.tool
```

### 常见崩溃原因

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `Address already in use` | 端口被占用 | `lsof -i :8524` 找到占用进程 |
| `ModuleNotFoundError` | 依赖缺失 | `pip install -r requirements.txt` |
| `sqlite3.OperationalError` | 数据库损坏 | 参考第 1 节 |
| `MemoryError` | 内存不足 | 增加系统内存或优化查询 |
| `Permission denied` | 文件权限 | `chmod -R 755 data/` |

---

## 6. 常见问题 FAQ

### Q: 如何查看系统当前状态？

```bash
# 健康检查
curl http://localhost:8524/api/health

# 系统状态 (CPU/内存/数据库)
curl http://localhost:8524/api/status

# 数据源连通性
curl http://localhost:8524/api/system/source-status
```

### Q: 如何手动触发数据采集？

```bash
curl -X POST http://localhost:8524/api/system/collect-manual
```

### Q: 数据库文件过大怎么办？

```bash
# 1. 执行 VACUUM 压缩
sqlite3 data/resonance.db "VACUUM;"

# 2. 清理旧数据 (保留 180 天)
sqlite3 data/resonance.db "DELETE FROM gex_strikes WHERE timestamp < datetime('now', '-180 days');"
sqlite3 data/resonance.db "DELETE FROM signal_alerts WHERE trigger_time < datetime('now', '-365 days');"

# 3. 再次 VACUUM
sqlite3 data/resonance.db "VACUUM;"
```

### Q: 如何查看当前信号评分？

```bash
curl http://localhost:8524/api/dashboard/scores | python -m json.tool
```

### Q: LLM 推理很慢怎么办？

- 检查 LLM 缓存命中率: 缓存模块 `backend/quant/llm_cache.py`
- 相同输入命中缓存时从 2s 降至 50ms
- 如果 OpenAI 响应慢，系统自动降级到 Anthropic 或模板

### Q: 如何更新配置？

```bash
# 查看当前配置
curl http://localhost:8524/api/config

# 更新配置
curl -X PUT http://localhost:8524/api/config \
  -H "Content-Type: application/json" \
  -d '{"fetch_interval_seconds": 120}'

# 恢复默认配置
curl -X POST http://localhost:8524/api/config/restore
```

### Q: 前端无法连接后端？

1. 检查 CORS 配置: `backend/config.py` 中 `cors_origins`
2. 确认前端构建: `cd frontend && npm run build`
3. 检查 Nginx 配置: `deploy/nginx.conf`

---

## 紧急联系流程

1. **P0 (服务完全不可用)**: 立即重启 → 通知团队 → 排查根因
2. **P1 (部分功能异常)**: 记录症状 → 尝试降级 → 排查根因
3. **P2 (性能下降)**: 监控指标 → 计划优化 → 下次维护窗口处理

---

> 最后更新: 2026-07-28 | 适用版本: v3.1
