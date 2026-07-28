# 待修复功能清单

> 基于代码深度验证生成，区分"代码存在但未集成"和"功能缺失"

---

## 一、安全鉴权加固

**状态**: ✅ 代码已实现并集成到 `main.py`

### 已验证
- [x] `backend/api/middleware/auth.py` — JWT 中间件已实现 (219 行)
- [x] `backend/api/middleware/rate_limit.py` — slowapi 限流已实现 (50 行)
- [x] `backend/main.py:176` — `init_rate_limiter(app)` 已调用
- [x] `backend/main.py:181` — `app.middleware("http")(jwt_write_middleware)` 已注册

### 需要验证
- [ ] 启动服务后，测试无 token 的 POST 请求是否返回 401
- [ ] 测试快速请求是否触发 429 限流

**结论**: 代码已完整集成，需运行时验证

---

## 二、数据库老化归档策略

**状态**: ✅ 代码已实现并注册到定时任务

### 已验证
- [x] `backend/utils/db_maintenance.py` — `archive_old_data(days=180)` 已实现
- [x] `backend/utils/db_maintenance.py` — `vacuum_and_analyze()` 已实现
- [x] `backend/utils/db_maintenance.py` — `backup_database_full()` / `backup_database_incremental()` 已实现
- [x] `backend/utils/scheduler.py` — 归档任务已注册到 APScheduler
- [x] `backend/main.py:88` — `start_scheduler()` 已在 lifespan 中调用

### 需要验证
- [ ] 手动执行 `archive_old_data()` 验证归档逻辑
- [ ] 检查 `gex_strikes_archive` 表是否被创建
- [ ] 验证定时任务是否按时触发

**结论**: 代码已完整集成，需运行时验证

---

## 三、贝叶斯权重自适应模块

**状态**: ✅ 已集成到评分流程

### 已验证
- [x] `backend/quant/bayesian_weights.py` — `BayesianWeightAdapter` 已实现 (411 行)
- [x] 支持 Beta-Binomial 共轭更新
- [x] 有完整的文档注释和使用示例

### 未集成
- [x] `backend/quant/scoring.py` 使用动态权重替代硬编码 `WEIGHTS`
- [x] `BayesianWeightAdapter` 已被 Pipeline 集成，评分后自动更新权重
- [x] 定时任务每日 07:00 UTC 调用 `update_weights()` 更新权重

### 需要修复
- [x] 修改 `scoring.py`，`calculate_score()` 使用动态权重替代硬编码 `WEIGHTS`
- [x] 在 Pipeline 评分阶段集成：每次评分后调用 `adapter.update()`
- [x] 添加定时任务：每日 07:00 UTC 根据最新 signal_outcomes 更新权重
- [x] 添加 API 端点：`GET /api/config/weights` 查看当前权重
- [x] 添加 API 端点：`POST /api/config/weights/reset` 重置为默认权重

---

## 四、validation_audit_log / gateway_snapshots 0 行异常修复

**状态**: ⚠️ 写入代码存在，但 Pipeline 未运行触发

### 已验证
- [x] `backend/pipeline/data_writer.py` — `DataWriter` 类已实现 (375 行)
- [x] `DataWriter.write_validation_audit()` 方法存在
- [x] `DataWriter.write_gateway_snapshot()` 方法存在
- [x] Pipeline 的 `run_cycle()` 会调用 DataWriter

### 未触发
- [ ] Pipeline 需要手动启动 (`GET /api/system/start-collect`)
- [ ] 启动后，DataWriter 会在每个采集周期写入审计日志和快照
- [ ] 当前数据库为空是因为 Pipeline 从未运行过

### 需要验证
- [ ] 启动服务后，调用 `GET /api/system/start-collect` 启动 Pipeline
- [ ] 等待一个采集周期（默认 60 秒）
- [ ] 查询 `SELECT COUNT(*) FROM validation_audit_log;` 验证有数据
- [ ] 查询 `SELECT COUNT(*) FROM gateway_snapshots;` 验证有数据

### 如果仍为 0 行
- [ ] 检查 `data_writer.py` 中写入逻辑是否被正确调用
- [ ] 检查 Pipeline 日志是否有写入错误
- [ ] 可能需要手动触发：`GET /api/system/collect-manual`

---

## 五、Grafana Dashboard JSON 配置

**状态**: ✅ 文件已存在且格式完整

### 已验证
- [x] `deploy/grafana_dashboard.json` — 286 行完整 JSON
- [x] 包含 `panels` 数组（System Overview、Service Status 等）
- [x] 包含 `targets` 配置 Prometheus 查询表达式
- [x] JSON 格式合法，可被 Grafana 导入

### 面板内容
- [x] System Overview — 服务状态、 uptime
- [x] 采集耗时面板
- [x] 信号频率面板
- [x] 数据库性能面板

### 需要操作
- [ ] 在 Grafana 中导入：`Configuration → Data Sources → Add → Prometheus`
- [ ] 导入 Dashboard：`Dashboards → Import → Upload JSON File → grafana_dashboard.json`
- [ ] 验证面板数据是否正确显示

**结论**: 配置文件完整，需在 Grafana 中导入使用

---

## 总结

| 项目 | 代码状态 | 集成状态 | 需要操作 |
|------|----------|----------|----------|
| JWT 鉴权 + Rate Limiting | ✅ 完整 | ✅ 已集成 | 运行时验证 |
| 数据库老化归档 | ✅ 完整 | ✅ 已集成 | 运行时验证 |
| 贝叶斯权重自适应 | ✅ 完整 | ✅ 已集成 | 运行时验证 |
| 0 行异常表 | ✅ 完整 | ⚠️ 需触发 | 启动 Pipeline |
| Grafana Dashboard | ✅ 完整 | N/A | 导入 Grafana |

---

## 修复优先级

### ~~🔴 高优先级~~
1. ~~**贝叶斯权重集成** — 修改 `scoring.py` 支持动态权重，Pipeline 集成~~ ✅ 已完成

### 🟡 中优先级
2. **启动 Pipeline 验证** — 确认 0 行异常表能正常写入
3. **运行时验证安全中间件** — 确认 JWT 和限流生效

### 🟢 低优先级
4. **Grafana 导入** — 运维操作，非代码问题
