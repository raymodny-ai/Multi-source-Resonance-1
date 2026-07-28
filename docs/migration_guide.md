# 多源共振监控系统 — 版本迁移指南

> 本文档描述从 V2.x 迁移到 V3.x 的完整步骤和变更说明。

---

## 目录

1. [版本概览](#1-版本概览)
2. [V2.x → V3.x 变更说明](#2-v2x--v3x-变更说明)
3. [数据库 Schema Diff](#3-数据库-schema-diff)
4. [迁移步骤](#4-迁移步骤)
5. [配置变更说明](#5-配置变更说明)
6. [API 兼容性](#6-api-兼容性)
7. [回滚方案](#7-回滚方案)

---

## 1. 版本概览

| 版本 | 架构 | 主要特性 |
|------|------|----------|
| V2.x | 单体架构，同步处理 | 基础 GEX 分析，单数据源，简单告警 |
| V3.0 | 三层解耦架构 V1.0 | EventBus，四维共振评分，React 前端 |
| V3.1 | 三层解耦架构 V2.0 | BFF 聚合，历史回放，Pipeline V2.0，双主题 |

---

## 2. V2.x → V3.x 变更说明

### 2.1 架构变更

| 变更项 | V2.x | V3.x | 影响 |
|--------|------|------|------|
| 后端框架 | Flask (同步) | FastAPI (async) | 所有路由需要重写 |
| 数据库 | 直连 SQLite | aiosqlite + WAL + 连接池 | 需迁移数据 |
| 数据流 | 定时轮询 | EventBus + asyncio | 新增事件订阅机制 |
| 前端 | Vue 2 | React 18 + Vite | 完全重写 |
| 配置 | YAML 文件 | pydantic-settings + .env | 配置格式变更 |
| 日志 | print 输出 | structlog JSON | 日志格式变更 |
| 部署 | 单进程 | Docker + systemd | 部署方式变更 |

### 2.2 目录结构变更

```
V2.x:                          V3.x:
├── app/                       ├── backend/
│   ├── models/                │   ├── api/
│   ├── views/                 │   ├── quant/
│   ├── services/              │   ├── fetchers/
│   └── utils/                 │   ├── models/
├── static/                    │   ├── eventbus/
├── templates/                 │   ├── pipeline/
├── config.yml                 │   ├── utils/
└── run.py                     │   ├── config.py
                               │   ├── database.py
                               │   └── main.py
                               ├── frontend/src/
                               ├── deploy/
                               ├── docs/
                               ├── scripts/
                               ├── data/
                               └── .env
```

### 2.3 数据源变更

| 数据源 | V2.x | V3.x | 变更 |
|--------|------|------|------|
| GEX | GEXMetrix only | GEXMetrix + SqueezeMetrics 降级 | 新增降级链 |
| VIX | 手动输入 | CBOE 自动采集 | 新增自动采集 |
| Crypto | 无 | Hyperliquid + CCData | 全新模块 |
| Darkpool | 单一 DIX | AXLFI + DBMF + StockGrid | 多维度暗池分析 |
| LLM | 无 | OpenAI + Anthropic 双 Provider | 全新模块 |

---

## 3. 数据库 Schema Diff

### 3.1 新增表

V3.x 相比 V2.x 新增以下表:

```sql
-- 新增: GEX 逐 strike 分布 (V2.x 仅有快照摘要)
CREATE TABLE gex_strikes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    timestamp   DATETIME NOT NULL,
    strike      REAL NOT NULL,
    call_gex    REAL NOT NULL DEFAULT 0,
    put_gex     REAL NOT NULL DEFAULT 0,
    call_oi     INTEGER NOT NULL DEFAULT 0,
    put_oi      INTEGER NOT NULL DEFAULT 0,
    call_vol    INTEGER NOT NULL DEFAULT 0,
    put_vol     INTEGER NOT NULL DEFAULT 0,
    net_gex     REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES gex_snapshots(id) ON DELETE CASCADE
);

-- 新增: GEX 日级历史 (SqueezeMetrics 回填)
CREATE TABLE gex_history (
    timestamp       DATETIME PRIMARY KEY,
    gex_local       REAL NOT NULL,
    gex_calibrated  REAL,
    alpha_factor    REAL,
    put_wall_level  REAL,
    flip_zone_lower REAL,
    flip_zone_upper REAL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增: Alpha 因子历史
CREATE TABLE alpha_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    symbol          TEXT NOT NULL DEFAULT 'SPX',
    alpha_raw       REAL,
    alpha_ewm_20d   REAL,
    alpha_ewm_60d   REAL,
    gex_metrix_net  REAL,
    gex_squeeze_net REAL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增: VIX 期限结构分析
CREATE TABLE vix_analysis (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    vix_spot              REAL,
    vx1                   REAL,
    vx2                   REAL,
    term_structure_ratio  REAL,
    term_structure_state  TEXT,
    panic_premium         REAL,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增: 加密衍生品
CREATE TABLE crypto_derivatives (
    timestamp          DATETIME PRIMARY KEY,
    btc_funding_rate   REAL NOT NULL,
    btc_oi             REAL,
    oi_change_1h       REAL,
    liquidation_spike  BOOLEAN,
    cryptoquant_elr    REAL,
    funding_anomaly    BOOLEAN,
    oi_crash           BOOLEAN,
    leverage_cleanup   BOOLEAN,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增: 数据校验审计日志
CREATE TABLE validation_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    source          TEXT NOT NULL,
    symbol          TEXT,
    check_type      TEXT NOT NULL,
    check_name      TEXT NOT NULL,
    passed          BOOLEAN NOT NULL,
    input_value     TEXT,
    expected_range  TEXT,
    severity        TEXT DEFAULT 'INFO',
    message         TEXT,
    raw_data_hash   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增: Gateway 快照
CREATE TABLE gateway_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    source          TEXT NOT NULL,
    payload_hash    TEXT,
    payload_size    INTEGER,
    layer1_output   TEXT,
    layer2_output   TEXT,
    status          TEXT DEFAULT 'OK',
    error_message   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 修改表

```sql
-- signal_alerts: 新增字段
ALTER TABLE signal_alerts ADD COLUMN hawkes_branching_ratio REAL;
-- V2.x 仅有: id, trigger_time, total_score, gex_score, vix_score, crypto_score,
--            darkpool_score, alert_level, details, acknowledged, created_at
-- V3.x 新增: hawkes_branching_ratio

-- gex_snapshots: 新增字段
ALTER TABLE gex_snapshots ADD COLUMN quality_score REAL;
ALTER TABLE gex_snapshots ADD COLUMN data_lag_seconds INTEGER;
ALTER TABLE gex_snapshots ADD COLUMN oi_coverage_pct REAL;
```

### 3.3 新增视图

```sql
-- V3.x 新增 5 个视图
CREATE VIEW v_latest_gex_snapshot AS ...;
CREATE VIEW v_signal_summary AS ...;
CREATE VIEW v_source_health AS ...;
CREATE VIEW v_daily_darkpool AS ...;
CREATE VIEW v_resonance_dashboard AS ...;
```

---

## 4. 迁移步骤

### 4.1 前置准备

```bash
# 1. 备份 V2.x 数据库
cp data/resonance.db data/resonance_v2_backup.db

# 2. 备份 V2.x 配置
cp config.yml config_v2_backup.yml

# 3. 确认 Python 版本 >= 3.12
python --version

# 4. 确认 Node.js 版本 >= 18
node --version
```

### 4.2 安装 V3.x

```bash
# 1. 克隆/更新代码到 V3.x
git checkout v3.1.0

# 2. 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. 安装 Python 依赖
uv sync
# 或: pip install -r requirements.txt

# 4. 安装前端依赖
cd frontend && npm install && cd ..
```

### 4.3 数据迁移

```bash
# 1. 创建 V3.x 数据库 (自动建表)
python -c "from backend.database import init_db; import asyncio; asyncio.run(init_db())"

# 2. 迁移 V2.x 数据到 V3.x
python scripts/migrate_v2_to_v3.py \
    --source data/resonance_v2_backup.db \
    --target data/resonance.db

# 3. 回填 90 天 GEX 历史
python scripts/backfill_gex_history.py --days 90

# 4. 验证数据完整性
sqlite3 data/resonance.db "PRAGMA integrity_check;"
sqlite3 data/resonance.db "SELECT COUNT(*) FROM signal_alerts;"
```

### 4.4 配置迁移

```bash
# 1. 创建 .env 文件
cp .env.example .env

# 2. 编辑 .env，填入 API Keys
vim .env
# 必填项:
#   GEXMETRX_API_KEY=your_key
#   JWT_SECRET=your_secret
# 可选项:
#   OPENAI_API_KEY=your_key
#   ANTHROPIC_API_KEY=your_key
#   TELEGRAM_BOT_TOKEN=your_token
```

### 4.5 启动验证

```bash
# 1. 启动 API 服务
python -m backend.main

# 2. 验证健康检查
curl http://localhost:8524/api/health

# 3. 验证数据源连通性
curl http://localhost:8524/api/system/source-status

# 4. 验证前端构建
cd frontend && npm run build && cd ..

# 5. 验证完整功能
curl http://localhost:8524/api/dashboard/scores
```

---

## 5. 配置变更说明

### 5.1 配置文件格式变更

V2.x 使用 `config.yml`:
```yaml
# V2.x config.yml
database:
  path: data/resonance.db
api:
  host: 0.0.0.0
  port: 8524
gexmetrix:
  api_key: xxx
```

V3.x 使用 `.env` + `pydantic-settings`:
```bash
# V3.x .env
DB_PATH=./data/resonance.db
HOST=0.0.0.0
PORT=8524
GEXMETRX_API_KEY=xxx
JWT_SECRET=your_secret
LOG_LEVEL=INFO
```

### 5.2 环境变量对照表

| V2.x (config.yml) | V3.x (.env) | 说明 |
|--------------------|-------------|------|
| `database.path` | `DB_PATH` | 数据库路径 |
| `api.host` | `HOST` | 监听地址 |
| `api.port` | `PORT` | 监听端口 |
| `gexmetrix.api_key` | `GEXMETRX_API_KEY` | GEXMetrix API Key |
| 无 | `JWT_SECRET` | JWT 签名密钥 (新增) |
| 无 | `OPENAI_API_KEY` | OpenAI API Key (新增) |
| 无 | `ANTHROPIC_API_KEY` | Anthropic API Key (新增) |
| 无 | `CORS_ORIGINS` | CORS 允许域名 (新增) |
| 无 | `LOG_LEVEL` | 日志级别 (新增) |

---

## 6. API 兼容性

### 6.1 不兼容变更

| V2.x 端点 | V3.x 端点 | 变更说明 |
|-----------|-----------|----------|
| `GET /api/gex/latest` | `GET /api/gex/{symbol}/latest` | 新增 symbol 参数 |
| `GET /api/signals` | `GET /api/signals/current` | 路径变更 |
| `POST /api/refresh` | `POST /api/system/collect-manual` | 路径和功能变更 |
| `GET /api/config` | `GET /api/config` | 响应格式变更 (JSON → Pydantic) |

### 6.2 新增端点

V3.x 新增 61+ 个 API 端点，详见 `docs/openapi_spec.md`。

### 6.3 响应格式变更

V2.x:
```json
{"status": "ok", "data": {...}}
```

V3.x:
```json
{"success": true, "message": "ok", "data": {...}}
```

---

## 7. 回滚方案

如果迁移失败需要回滚到 V2.x:

```bash
# 1. 停止 V3.x 服务
systemctl stop multi-resonance

# 2. 恢复 V2.x 数据库
cp data/resonance_v2_backup.db data/resonance.db

# 3. 切换回 V2.x 代码
git checkout v2.x

# 4. 恢复 V2.x 配置
cp config_v2_backup.yml config.yml

# 5. 重启 V2.x 服务
python run.py
```

---

> 最后更新: 2026-07-28 | 适用版本: v2.x → v3.1
