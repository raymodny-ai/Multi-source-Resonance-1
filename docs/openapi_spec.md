# 多源共振监控系统 — API 接口文档索引

> 基于 v3.1 版本，共 61 个端点。FastAPI 自动生成 Swagger UI: `http://localhost:8524/docs`

---

## 认证说明

### JWT 认证

部分写操作端点需要 JWT Bearer Token:

```bash
# 获取 Token
curl -X POST http://localhost:8524/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# 响应
{"access_token": "eyJhbGci...", "token_type": "bearer"}

# 使用 Token
curl -H "Authorization: Bearer eyJhbGci..." http://localhost:8524/api/config
```

### 公开端点

大部分 GET 端点无需认证，可直接访问。

---

## 端点列表

### 一、健康 & 系统 (7 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 1 | GET | `/api/health` | 健康检查 | 否 |
| 2 | GET | `/api/status` | 系统状态 (CPU/内存/连接数) | 否 |
| 3 | GET | `/api/metrics` | Prometheus 风格指标 | 否 |
| 4 | GET | `/api/system/source-status` | 8 数据源连通性 | 否 |
| 5 | GET | `/api/system/logs/stream` | 实时日志流 (SSE) | 否 |
| 6 | GET | `/api/system/auto-polling` | 当前自动轮询状态 | 否 |
| 7 | PUT | `/api/system/auto-polling` | 切换自动轮询 | 否 |

#### 请求/响应示例

**GET /api/health**
```json
// Response 200
{
  "status": "ok",
  "timestamp": "2026-07-28T12:00:00+00:00",
  "version": "3.1.0",
  "uptime_seconds": 3600.5
}
```

**GET /api/status**
```json
// Response 200
{
  "cpu_percent": 15.2,
  "memory_percent": 45.8,
  "memory_used_mb": 512.3,
  "memory_total_mb": 2048.0,
  "db_size_mb": 128.5,
  "active_connections": 3,
  "uptime_seconds": 3600.5
}
```

---

### 二、仪表盘聚合 (8 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 8 | GET | `/api/dashboard/scores` | 当前四维共振评分 | 否 |
| 9 | GET | `/api/dashboard/recent-alerts` | 最近告警 | 否 |
| 10 | GET | `/api/dashboard/resonance-history` | 共振分数历史 | 否 |
| 11 | GET | `/api/dashboard/cross-asset-heatmap` | 跨资产热力图 | 否 |
| 12 | GET | `/api/dashboard/gex-curve?days=N` | GEX 长期曲线 (默认 90 天) | 否 |
| 13 | GET | `/api/dashboard/multi-channel-curve` | 三通道 (GEX+VEX+CHEX) 曲线 | 否 |
| 14 | GET | `/api/dashboard/data-quality` | 流动性门控质量评分 | 否 |
| 15 | GET | `/api/dashboard/pipeline-metrics` | Pipeline V2.0 运行指标 | 否 |

#### 请求/响应示例

**GET /api/dashboard/scores**
```json
// Response 200
{
  "normalized_score": 62.5,
  "raw_score": 5.0,
  "raw_max": 8.0,
  "level": "LEVEL_2",
  "dimension_scores": {
    "gex": 75.0,
    "vix": 60.0,
    "crypto": 45.0,
    "darkpool": 80.0
  },
  "dimension_weights": {
    "gex": 2.5,
    "vix": 1.5,
    "crypto": 2.0,
    "darkpool": 2.0
  },
  "signals": ["gex_strong", "darkpool_strong"],
  "timestamp": "2026-07-28T12:00:00+00:00"
}
```

---

### 三、GEX 元数据 (8 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 16 | GET | `/api/gex/symbols` | 所有可用标的 + 新鲜度 | 否 |
| 17 | GET | `/api/gex/summary` | 6 标的最新摘要 | 否 |
| 18 | GET | `/api/gex/history?days=N` | SqueezeMetrics 90 天历史 | 否 |
| 19 | GET | `/api/gex/{symbol}/latest` | GEXMetrix 最新快照摘要 | 否 |
| 20 | GET | `/api/gex/{symbol}/history?days=N` | GEXMetrix 时间序列 (≤3 天) | 否 |
| 21 | GET | `/api/gex/{symbol}/levels` | 关键价位 | 否 |
| 22 | GET | `/api/gex/{symbol}/strikes?limit=N` | 逐 strike GEX/OI 分布 | 否 |
| 23 | GET | `/api/gex/{symbol}/dashboard-view` | BFF 聚合接口 | 否 |

---

### 四、VIX / 暗池 / 标的 (3 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 24 | GET | `/api/vix/history?days=N` | VIX 期限结构历史 | 否 |
| 25 | GET | `/api/darkpool/history?days=N` | 暗池指标历史 | 否 |
| 26 | GET | `/api/tickers` | 可监控标的列表 | 否 |

---

### 五、信号 & 告警 (9 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 27 | GET | `/api/signals/current` | 当前活跃信号 | 否 |
| 28 | GET | `/api/signals/history` | 历史信号 | 否 |
| 29 | POST | `/api/signals/{id}/acknowledge` | 确认信号 | 否 |
| 30 | GET | `/api/alerts` | 告警列表 | 否 |
| 31 | POST | `/api/alerts/{id}/acknowledge` | 确认告警 | 否 |
| 32 | GET | `/api/incidents` | Incident 列表 | 否 |
| 33 | GET | `/api/incidents/{id}` | Incident 详情 | 否 |
| 34 | PUT | `/api/incidents/{id}/review` | 标记已复盘 | 否 |
| 35 | GET | `/api/incidents/{id}/export` | 导出 JSON 报告 | 否 |

#### 请求/响应示例

**GET /api/signals/current**
```json
// Response 200
{
  "id": 42,
  "trigger_time": "2026-07-28T12:00:00+00:00",
  "total_score": 3.8,
  "gex_score": 2.1,
  "vix_score": 1.2,
  "crypto_score": 1.5,
  "darkpool_score": 1.8,
  "alert_level": "LEVEL_3",
  "hawkes_branching_ratio": 0.45,
  "acknowledged": false,
  "details": "{\"signals\": [\"gex_strong\", \"multi_dimension_resonance\"]}"
}
```

---

### 六、V3.1 快照 API (4 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 36 | GET | `/api/snapshots` | 快照时间线列表 | 否 |
| 37 | GET | `/api/snapshots/stats` | 快照统计摘要 | 否 |
| 38 | GET | `/api/snapshots/{timestamp}` | 获取指定时刻快照 | 否 |
| 39 | POST | `/api/snapshots/capture` | 手动触发快照捕获 | 否 |

---

### 七、配置 & LLM (7 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 40 | GET | `/api/config` | 当前配置 | 否 |
| 41 | GET | `/api/config/defaults` | 默认配置 | 否 |
| 42 | GET | `/api/config/audit` | 配置变更审计 | 否 |
| 43 | PUT | `/api/config` | 更新配置 | 否 |
| 44 | POST | `/api/config/restore` | 还原到默认 | 否 |
| 45 | GET | `/api/llm/status` | LLM provider 状态 | 否 |
| 46 | POST | `/api/llm/analyze` | 触发 LLM 分析 | 否 |

#### 请求/响应示例

**POST /api/llm/analyze**
```json
// Request
{
  "include_gex": true,
  "include_vix": true,
  "include_crypto": true,
  "include_darkpool": true
}

// Response 200
{
  "score": 72.5,
  "level": "LEVEL_2",
  "signals": ["llm_openai_success"],
  "details": {
    "llm_provider": "openai",
    "analysis_text": "Market conditions suggest...",
    "confidence": 0.75,
    "model_used": "gpt-4o",
    "timestamp": "2026-07-28T12:00:00+00:00"
  }
}
```

---

### 八、通知 & 认证 (5 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 47 | GET | `/api/notifications/config` | 通知渠道配置 | 否 |
| 48 | PUT | `/api/notifications/config` | 更新通知配置 | 否 |
| 49 | GET | `/api/notifications/status` | 通知状态 | 否 |
| 50 | POST | `/api/notifications/test` | 测试通知发送 | 否 |
| 51 | POST | `/api/auth/login` | 登录 (JWT) | 否 |

---

### 九、WebSocket (1 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 52 | WS | `/ws` | WebSocket 长连接 | 否 |

#### 消息格式

```json
// Client → Server: Subscribe
{"action": "subscribe", "topics": ["SIGNAL", "GEXMETRIX_SNAPSHOT"]}

// Server → Client: Event
{
  "topic": "SIGNAL",
  "payload": {
    "level": "LEVEL_3",
    "score": 3.8,
    "dimensions": {"gex": 2.1, "vix": 1.2, "crypto": 1.5, "darkpool": 1.8}
  },
  "timestamp": "2026-07-28T12:00:00+00:00"
}
```

---

### 十、手动采集 & 其他 (9 端点)

| # | 方法 | 路径 | 说明 | 认证 |
|---|------|------|------|------|
| 53 | POST | `/api/system/collect-manual` | 手动触发 8 数据维度采集 | 否 |
| 54 | GET | `/api/gex/{symbol}/dashboard-view` | GEX BFF 聚合 | 否 |
| 55 | GET | `/api/crypto/latest` | 加密衍生品最新数据 | 否 |
| 56 | GET | `/api/crypto/history` | 加密衍生品历史 | 否 |
| 57 | GET | `/api/darkpool/latest` | 暗池最新数据 | 否 |
| 58 | GET | `/api/analysis/gex` | GEX 分析详情 | 否 |
| 59 | GET | `/api/analysis/vix` | VIX 分析详情 | 否 |
| 60 | GET | `/api/analysis/crypto` | 加密分析详情 | 否 |
| 61 | GET | `/api/analysis/darkpool` | 暗池分析详情 | 否 |

---

## 通用错误响应

所有端点在出错时返回统一格式:

```json
// 400 Bad Request
{
  "success": false,
  "message": "Invalid parameter: symbol must be one of SPX, SPY, QQQ, IWM, NDX, VIX",
  "detail": null
}

// 401 Unauthorized
{
  "success": false,
  "message": "Not authenticated",
  "detail": "Missing or invalid Authorization header"
}

// 404 Not Found
{
  "success": false,
  "message": "Resource not found",
  "detail": "Signal with id=999 does not exist"
}

// 500 Internal Server Error
{
  "success": false,
  "message": "Internal server error",
  "detail": "Database connection failed"
}
```

---

## 速率限制

当前版本无全局速率限制。建议客户端:
- GET 请求: ≤ 60 次/分钟
- POST/PUT 请求: ≤ 10 次/分钟
- WebSocket: 单 IP 最多 5 个并发连接

---

> 完整交互式文档: `http://localhost:8524/docs` (Swagger UI)
> ReDoc 文档: `http://localhost:8524/redoc`
