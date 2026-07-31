# 数据获取规则修改与错误提示增强 — 待办清单

> 生成时间：2026-07-28 | 状态：**已完成**（2026-07-31）
>
> **完成度**：P0/P1/P2 全部落地；后端 179 单元/集成测试全部通过；前端 `npm run build`（vue-tsc 类型检查 + vite 构建）0 错误通过。

---

## 核心 Bug 发现

**`_meta.is_mock` 数据完整性问题**：14 个 fetcher 的 `fetch()` 方法在内部 try/except 中直接返回 mock 数据而不抛出异常，导致 `_wrap_result(data, is_mock=False)` 将 mock 数据**错误标记为真实数据**。前端无法区分真实/模拟数据，`mock_count` 统计始终为 0。

**修复方案**：在 `BaseFetcher.fetch_with_retry()` 内统一处理 `_internal_mock` 标记 + 新增 `mock_reason`/`retry_count` 元字段，前端 DashboardView、store、组件层均可正确显示。

---

## 一、后端 Fetcher 层（P0 — 核心 Bug 修复）

### 1.1 `backend/fetchers/base.py`（270 行）

- [x] **1.1.1** `_wrap_result()` 方法签名增加 `mock_reason` 和 `retry_count` 参数
- [x] **1.1.2** `_meta` 字典增加 `mock_reason`（`"api_key_absent"` / `"fetch_failed_fallback"` / `"internal_fallback"`）和 `retry_count` 字段
- [x] **1.1.3** `fetch_with_retry()` 三处 `_wrap_result` 调用更新：
  - mock 模式直接返回 → `mock_reason="api_key_absent"`
  - fetch 成功 → `retry_count=attempt`
  - 重试耗尽回退 → `mock_reason="fetch_failed_fallback"`, `error=str(last_error)`
- [x] **1.1.4** `fetch_with_retry()` 增加 `_internal_mock` 检测：在 `data = await self.fetch()` 之后检查 `data.pop("_internal_mock", False)`，正确设置 `is_mock`

### 1.2 14 个 Fetcher 文件 — 统一增加 `_internal_mock` 标记

每个 fetcher 的 `fetch()` 方法中，except 分支返回 mock 数据前需设置 `mock["_internal_mock"] = True`：

| 序号 | 文件 | fetch() mock 返回行号 | 状态 |
|------|------|----------------------|------|
| - [x] 1.2.1 | `vix_fetcher.py` | 第 98 行 | ✅ |
| - [x] 1.2.2 | `darkpool_fetcher.py` | 第 35 行 | ✅ |
| - [x] 1.2.3 | `crypto_fetcher.py` | 第 58 行 | ✅ |
| - [x] 1.2.4 | `options_greeks_fetcher.py` | 第 70/77/133 行（3 处） | ✅ |
| - [x] 1.2.5 | `yfinance_fetcher.py` | 第 72 行 | ✅ |
| - [x] 1.2.6 | `squeezemetrics_fetcher.py` | 第 41 行 | ✅ |
| - [x] 1.2.7 | `coinglass_fetcher.py` | 第 42 行 | ✅ |
| - [x] 1.2.8 | `finra_fetcher.py` | 第 50 行 | ✅ |
| - [x] 1.2.9 | `ccdata_fetcher.py` | 第 42 行 | ✅ |
| - [x] 1.2.10 | `vix_term_fetcher.py` | 第 36 行 | ✅ |
| - [x] 1.2.11 | `put_call_fetcher.py` | 第 35 行 | ✅ |
| - [x] 1.2.12 | `stockgrid_fetcher.py` | 第 50 行 | ✅ |
| - [x] 1.2.13 | `dbmf_fetcher.py` | 第 42 行 | ✅ |
| - [x] 1.2.14 | `tradier_fetcher.py` | 第 46 行 | ✅ |

补充：除上面 14 个外，下列 fetcher 也在 mock 回退路径加上了 `_internal_mock=True` 标记，确保完整覆盖：`flow_fetcher.py`、`sentiment_fetcher.py`、`sector_fetcher.py`、`macro_fetcher.py`。

### 1.3 `options_greeks_fetcher.py` 和 `vix_fetcher.py` — 删除自行写入的 `_meta`

- [x] **1.3.1** `options_greeks_fetcher.py` 第 135-143 行：删除 `fetch()` 真实数据路径中的 `_meta` 字段（由 `_wrap_result()` 统一管理）
- [x] **1.3.2** `options_greeks_fetcher.py` 第 233-243 行：删除 `_mock_data()` 中的 `_meta` 字段
- [x] **1.3.3** `vix_fetcher.py` 第 190 行：删除 `_build_payload()` 中的 `_meta` 字段
- [x] **1.3.4** `vix_fetcher.py` 第 210 行：`_mock_data()` 中 `payload["_meta"]["source"] = "mock"` 改为 `payload["_internal_mock"] = True`

---

## 二、后端 Pipeline 层

### 2.1 `backend/pipeline/concurrent_executor.py`（314 行）

- [x] **2.1.1** `FetchResult` 数据类增加 `mock_reason: Optional[str]` 和 `retry_count: int` 字段
- [x] **2.1.2** `_execute_single()` 方法：从 `_meta` 提取 `mock_reason` 和 `retry_count`，传入 FetchResult
- [x] **2.1.3** `success` 语义修正：`success=True` 表示"数据可用"（无论真实/mock），`error` 字段区分错误
- [x] **2.1.4** `ExecutionReport` 统计逻辑更新：`success_count` = 真实成功数，`error_count` = 有 error 的数量
- [x] **2.1.5** 超时和异常分支的 FetchResult 补充新字段默认值
- [x] **2.1.6** `_publish_fetch_result()` 方法：当 `is_mock=True` 时额外发布 `DATA_MOCK_FALLBACK` 事件

### 2.2 `backend/pipeline/pipeline.py`（528 行）

- [x] **2.2.1** `run_cycle()` 返回字典增加 `source_details` 字段（per-source 详情列表）
- [x] **2.2.2** `run_cycle()` 返回字典增加 `write_results` 字段
- [x] **2.2.3** `run_cycle()` 末尾发布 `PIPELINE_CYCLE_COMPLETE` 事件
- [x] **2.2.4** 新增 `last_report` property，方便 API 直接消费

### 2.3 `backend/pipeline/data_writer.py`（537 行）

- [x] **2.3.1** `write_fetch_results()` 返回类型从 `dict[str, int]` 改为 `dict[str, dict]`（含 `count` 和 `error`）
- [x] **2.3.2** 同步更新 `pipeline.py` 第 412 行对 `written` 的消费方式

---

## 三、后端 API 路由层

### 3.1 `backend/api/routes/system.py`（207 行）

- [x] **3.1.1** `collect-manual` 端点：从 report 中提取 `source_details` 替换硬编码空数组，增加 `mock_count`
- [x] **3.1.2** `source-status` 端点：从 pipeline `last_report` 获取 per-source 信息，填充 `last_error`/`is_mock`/`mock_reason`
- [x] **3.1.3** 新增 `GET /api/system/collection-detail` 端点：返回最近一次 pipeline cycle 的 per-source 详情

### 3.2 `backend/api/routes/dashboard.py`（269 行）

- [x] **3.2.1** `dashboard_view()` 返回 dict 增加 `_meta.mock_sources` 列表
- [x] **3.2.2** `data-quality` 端点增加 `mock_sources` 字段

### 3.3 `backend/models/common.py`（73 行）

- [x] **3.3.1** `SourceStatus` 增加 `is_mock: bool` 和 `mock_reason: Optional[str]` 字段
- [x] **3.3.2** 新增 `CollectionSourceDetail` 模型
- [x] **3.3.3** 新增 `CollectionReport` 模型

---

## 四、后端 EventBus + WebSocket 层

### 4.1 `backend/eventbus/events.py`（52 行）

- [x] **4.1.1** 新增事件类型 `DATA_MOCK_FALLBACK = "data.mock.fallback"`
- [x] **4.1.2** 新增事件类型 `PIPELINE_CYCLE_COMPLETE = "pipeline.cycle.complete"`

### 4.2 `backend/api/websocket.py`（187 行）

- [x] **4.2.1** `topics_to_bridge` 列表增加 `DATA_MOCK_FALLBACK` 和 `PIPELINE_CYCLE_COMPLETE`

---

## 五、前端 API 层

### 5.1 `frontend/src/api/client.ts`

- [x] **5.1.1** 响应拦截器增加全局错误通知：`window.dispatchEvent(new CustomEvent('msr-api-error', ...))`
- [x] **5.1.2** 超时配置从 30000 增加到 60000（collect-manual 等长耗时端点需要）

### 5.2 `frontend/src/api/websocket.ts`

- [x] **5.2.1** 增加 `_connectionState` 属性和 `isConnected`/`connectionState` getter
- [x] **5.2.2** `connect()`/`onopen`/`onclose` 中更新 `_connectionState`
- [x] **5.2.3** 增加 `emitStatusChange()` 方法，通过 `CustomEvent('msr-ws-status')` 广播
- [x] **5.2.4** `WSMessage` 接口增加可选 `level` 字段

### 5.3 `frontend/src/api/system.ts`

- [x] **5.3.1** `SourceStatus` 接口增加 `last_error`/`is_mock`/`mock_reason` 字段
- [x] **5.3.2** 新增 `CollectionSourceDetail` 和 `CollectionReport` 接口
- [x] **5.3.3** 新增 `getCollectionDetail()` API 函数
- [x] **5.3.4** `triggerManualCollection()` 返回类型改为 `CollectionReport`

### 5.4 `frontend/src/api/dashboard.ts`

- [x] **5.4.1** `DashboardData` 接口增加 `_meta` 可选字段

---

## 六、前端 Store 层

### 6.1 `frontend/src/stores/market.ts`

- [x] **6.1.1** 增加 `dimensionErrors` 和 `mockSources` 状态
- [x] **6.1.2** `fetchAllDimensions()` 各 `.catch()` 回调记录错误到 `dimensionErrors`
- [x] **6.1.3** `fetchDashboard()` 提取 `mockSources` 从响应 `_meta`
- [x] **6.1.4** WebSocket `liveHandler` 增加 `data.mock.fallback` 和 `pipeline.cycle.complete` 事件处理
- [x] **6.1.5** error 自动清除逻辑（30 秒后清除）
- [x] **6.1.6** return 增加 `dimensionErrors`/`mockSources`/`hasMockData` 导出

### 6.2 `frontend/src/stores/system.ts`

- [x] **6.2.1** 每个 action 开头清除 `error.value = null`
- [x] **6.2.2** 增加 `collectionDetail` 和 `sourceErrors` 状态
- [x] **6.2.3** `collectManual()` 解析返回到 `collectionDetail`
- [x] **6.2.4** `fetchSourceStatus()` 提取 per-source 错误到 `sourceErrors`
- [x] **6.2.5** return 增加新导出

### 6.3 `frontend/src/stores/signals.ts`

- [x] **6.3.1** 每个 action 开头清除 `error.value = null`

---

## 七、前端组件层

### 7.1 `frontend/src/components/dashboard/SourceStatusCard.vue`

- [x] **7.1.1** 模板增加 MOCK 标识徽章（`v-if="source.is_mock"`）
- [x] **7.1.2** 模板增加 `last_error` 显示（红色警告）
- [x] **7.1.3** script 增加 `mockReasonText` 计算属性和 `truncate()` 辅助函数
- [x] **7.1.4** style 增加 `.badge-mock` 和 `.source-error` 样式

### 7.2 `frontend/src/components/dashboard/SignalCard.vue`

- [x] **7.2.1** 增加 mock 数据警告提示（`v-if="hasMockWarning"`）

### 7.3 `frontend/src/views/DashboardView.vue`

- [x] **7.3.1** 增加 Mock 数据警告横幅（黄色，可关闭）
- [x] **7.3.2** 增加全局错误横幅（红色）
- [x] **7.3.3** 增加 WebSocket 断连警告横幅
- [x] **7.3.4** 数据摘要卡片区分"无数据"和"获取失败"（`value-error` 样式）
- [x] **7.3.5** script 使用 `wsClient.isConnected` 替代 `pollStatus()` 中的 WS hack
- [x] **7.3.6** 删除 `pollStatus()` 中的 WS 状态 hack 代码
- [x] **7.3.7** style 增加 `.mock-warning-banner`/`.error-banner`/`.ws-warning-banner`/`.value-error` 样式

### 7.4 新增 `frontend/src/components/common/ErrorToast.vue`

- [x] **7.4.1** 全局错误 toast 组件：监听 `msr-api-error` 事件
- [x] **7.4.2** 每个 toast 5 秒自动消失，最多同时显示 3 个
- [x] **7.4.3** 显示在页面右下角，点击可关闭

### 7.5 新增 `frontend/src/components/common/MockDataBanner.vue`

- [x] **7.5.1** 可复用 mock 数据警告横幅组件（props: `sources`/`dismissible`）

### 7.6 `frontend/src/App.vue`

- [x] **7.6.1** 全局挂载 `ErrorToast` 组件

---

## 八、配置文件

### 8.1 `backend/config.py`（91 行）

- [x] **8.1.1** `is_mock_mode()` 方法 docstring 更新，说明仅 GEXMetrix/AXLFI 使用

---

## 执行优先级

| 优先级 | 范围 | 文件数 | 说明 |
|--------|------|--------|------|
| **P0** | 一（1.1-1.3）+ 二（2.1-2.3）+ 三（3.1, 3.3） | ~20 | 核心 Bug 修复 + 数据流打通 |
| **P1** | 四 + 五 + 六 + 七（7.1-7.3） | ~12 | 前端可见改善 |
| **P2** | 七（7.4-7.6）+ 八 | ~4 | 增强完善 |

---

## 验证结果

### 后端测试

| 范围 | 用例数 | 通过 | 耗时 |
|------|--------|------|------|
| `backend/tests/unit` | 150 | 150 | ~6.2s |
| `backend/tests/integration` | 29 | 29 | ~5.8s |
| **合计** | **179** | **179** | **~12.0s** |

> 运行命令：`pytest backend/tests/unit backend/tests/integration -q`

### 前端构建

- `npm run build`（`vue-tsc --noEmit` + `vite build`）✅ 通过（2.37s）—— 类型检查与产物构建均 0 错误。

### 端到端连通性

- 后端 `DATA_MOCK_FALLBACK` 事件 → EventBus 桥接 → WebSocket 广播 → 前端 `WsStore` 接收 → `market.ts` 更新 `dimensionErrors`/`mockSources` → `DashboardView`/`SourceStatusCard` 显示 MOCK 徽章 + 全局横幅。
- 后端 `PIPELINE_CYCLE_COMPLETE` 事件 → 前端刷新 `system.ts.collectionDetail` 与 `system-store.mockSources`。
- API 任何超时/错误 → `client.ts` 拦截器广播 `msr-api-error` → `ErrorToast` 弹窗。

---

## 风险提示（已完成）

1. **`success` 语义变更**：`concurrent_executor.py` 中 `success` 从"真实成功"变为"数据可用"，影响日志和监控指标。✅ 已通过 pipeline 层 `success_count`、`error_count`、`mock_count` 三层统计保持可观测性。
2. **14 个 fetcher 一致性**：遗漏任何一个 `_internal_mock` 标记都会导致该 fetcher 的 mock 数据仍被标记为真实数据。✅ 已覆盖所有 14 个 fetcher，外加 4 个补充 fetcher。
3. **`data_writer.py` 返回类型变更**：从 `dict[str, int]` 变为 `dict[str, dict]`，需同步更新 `pipeline.py`。✅ 已同步。
4. **前端 `dimensionErrors` key 命名**：需与 API 返回的维度名一致（`gex`/`vix`/`crypto`/`darkpool`）。✅ 已通过前端 store 字段映射保证一致。
5. **WebSocket 消息向后兼容**：新增 `level` 字段为可选，旧客户端不受影响。✅ 字段为可选，向后兼容。
