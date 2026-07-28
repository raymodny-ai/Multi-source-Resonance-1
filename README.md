# 多源共振监控系统 — Multi-source Resonance

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3-61dafb)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![Vite](https://img.shields.io/badge/Vite-8.0-646cff)](https://vitejs.dev)
[![ECharts](https://img.shields.io/badge/ECharts-6.1-e43961)](https://echarts.apache.org)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57)](https://sqlite.org/wal.html)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-5-ff4154)](https://tanstack.com/query)
[![Status](https://img.shields.io/badge/v3.1-Latest-success)](#)

> 基于 **三层解耦架构 V2.0** 的多维度金融监控系统。实时追踪美股暗盘资金、做市商 Gamma 敞口、VIX 期限结构、加密杠杆清洗及跨资产共振，通过 **四维度 Regime Transition 评分** 自动识别"流动性清算衰竭"级抄底信号，多渠道推送告警。Web UI 基于 **React + Vite + ECharts + TanStack Query** 构建，后端采用 **FastAPI + asyncio EventBus + WebSocket**。V3.1 新增 **历史回放 (Time-Travel)** 功能。

---

## 📑 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [数据源矩阵](#3-数据源矩阵)
4. [数据架构](#4-数据架构)
5. [API 接口文档](#5-api-接口文档)
6. [后端设计](#6-后端设计)
7. [前端设计](#7-前端设计)
8. [核心业务逻辑](#8-核心业务逻辑)
9. [快速开始](#9-快速开始)
10. [部署](#10-部署)
11. [测试](#11-测试)
12. [监控标的](#12-监控标的)
13. [版本演进](#13-版本演进)
14. [许可证](#14-许可证)

---

## 1. 项目概述

### 1.1 业务目标

**核心命题**: 在美股市场识别"**流动性清算衰竭**"(Liquidity Cascade Exhaustion) 级抄底信号 — 即做市商对冲完毕、跨资产杠杆出清、Regime 从 Negative Gamma 翻转为 Positive Gamma 后的低点。

**解决方案**: 不是单一指标，而是 **多源共振** —
- 当 **GEX 转正**(做市商从空 Gamma 反转为多 Gamma) + **VIX 期限倒挂缓解** + **加密杠杆清洗** + **暗池 DIX 底背离** **四维同时触发**时，信号置信度最高。

### 1.2 核心能力

| 能力 | 描述 |
|------|------|
| **8 个数据维度** | GEXMetrix / SqueezeMetrics / FINRA / yfinance / VIX / 加密衍生品 / AXLFI 暗盘 / DBMF 均线 |
| **三层解耦 V2.0** | Layer1 纯数学计算 → Layer2 JSON 网关 → Layer3 LLM 推理(可独立替换) |
| **四维共振评分** | GEX + VIX + Crypto + Darkpool，满 5.0，LEVEL_3 阈值 3.5 |
| **Hawkes AR(1)** | OLS 自回归替代 corrcoef，精确自激分支比测算 |
| **逐 strike 真实数据** | GEXMetrix options[] 解析，1666+ strikes 入库，前端真实可视化 |
| **90 天历史回填** | SqueezeMetrics CSV 回填到 gex_history，曲线完整时间序列 |
| **BFF 聚合接口** | `/api/gex/{symbol}/dashboard-view` 一次返回 6 个 section |
| **WebSocket 实时流** | 长连接 Push 信号、告警、状态变更 |
| **降级容错** | Hyperliquid → CCData、yfinance → FINRA 双向降级 |
| **数据校验防线** | Pandera + Greeks 边界 + Put-Call Parity + 套利 + Isolation Forest |
| **BS 向量化引擎** | py-vollib-vectorized 批量 Greeks |
| **多渠道告警** | Email / Telegram / Discord 并发推送 |
| **LLM 推理** | GPT-4o / Claude 自动生成报告 |
| **回测引擎** | 历史信号回放、Sharpe / MaxDD / WinRate |
| **完整 Web UI** | React + Vite + ECharts 6 + TanStack Query 仪表盘 |
| **V3.0 玻璃拟态** | 设计令牌 + 双主题 + GlassCard + LiveTape |
| **V3.1 历史回放** | 快照时间线 + TimelineReplay + SnapshotGallery + 0.5x-4x 倍速 |

### 1.3 v3.1 当前状态(2026-07-28)

- **后端**: FastAPI 监听 `0.0.0.0:8524`，48+ 个 REST 路由 + WebSocket
- **数据库**: SQLite (WAL)，11 张表，主要数据表行数: `gex_strikes` 3332 / `dark_pool_metrics` 253 / `gex_history` 103 / `gex_snapshots` 90+ / `vix_analysis` 7
- **前端**: Vite 8.0 构建，ECharts 6.1 图表，18 个组件，15 个 API 模块
- **采集**: 每日美东 20:00 批量 + 手动触发 (`POST /api/system/collect-manual`)，8 个数据维度全健康
- **V3.1**: 快照自动记录 (5 分钟节流)，TimelineReplay 回放控制，SnapshotGallery 快照画廊

---

## 2. 系统架构

### 2.1 总体架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite + ECharts 6)                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │Dashboard │ Gamma    │ Signals  │ Alerts   │ Config   │ LLM      │  │
│  │+ Replay  │ Dashboard│ Panel    │ Center   │ Panel    │ Analysis │  │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘  │
│       │ TanStack Query (BFF dashboard-view 优先)                     │
└───────┼──────────────────────┬─────────────────────────────────────────┘
        │ REST (48+ 路由)       │ WebSocket
        ▼                       ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      FastAPI Server (8524)                            │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   REST API Layer (api_server.py)                │ │
│  │  /api/dashboard/*  /api/signals/*  /api/gex/*  /api/alerts/*    │ │
│  │  /api/snapshots/*  /api/system/*  /api/config  /api/llm/*      │ │
│  └────────────────────────┬─────────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │                 asyncio EventBus (pub/sub)                       │ │
│  │   Topics: GEXMETRIX_SNAPSHOT / SIGNAL / INCIDENT / CONFIG       │ │
│  └────────────────────────┬─────────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │           RESTPollScheduler (asyncio + APScheduler)             │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │   Data Fetcher Layer (8 数据维度)                           │  │ │
│  │  │   ┌──────────┬──────────┬──────────┬─────────────────┐   │  │ │
│  │  │   │GEXMetrix │SqueezeM. │FINRA/    │AXLFI/DBMF/      │   │  │ │
│  │  │   │fetcher   │fetcher   │yfinance  │Hyperliquid      │   │  │ │
│  │  │   └──────────┴──────────┴──────────┴─────────────────┘   │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │           │                                                       │ │
│  │           ▼                                                       │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │   Signal Pipeline (V2.0 三层解耦)                         │  │ │
│  │  │   Layer1: 数学计算  Layer2: JSON 网关  Layer3: LLM 推理 │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │   SQLite (WAL mode)          │
                    │   database/monitoring.db    │
                    └──────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   Multi-channel Notifier     │
                    │   Email / Telegram / Discord │
                    └──────────────────────────────┘
```

### 2.2 三层解耦 V2.0 架构

**核心设计原则**: 数学计算与 LLM 推理解耦，任意一层可独立替换/降级。

| Layer | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **Layer1 — 数学计算** | 纯 Python/numpy/pandas 计算 GEX、Z-Score、相关性、EMA、动量反转等指标 | 原始 OHLCV / OI / Greeks | 数值指标 + 触发布尔位 |
| **Layer2 — JSON 网关** | 把 Layer1 输出序列化为标准化 JSON，作为契约边界；对接评分/告警逻辑 | Layer1 数值输出 | 评分结果 + 触发原因 + 上下文 |
| **Layer3 — LLM 推理** | 接收 Layer2 JSON，生成人类可读报告(告警文案、抄底分析)；API 失败可降级到模板 | Layer2 JSON + 历史 context | 自然语言报告 |

**优点**:
- Layer3 不可用时系统仍能跑(降级到模板)
- Layer1 可独立做单元测试(无副作用)
- Layer2 JSON schema 是公开契约，跨语言可对接

### 2.3 异步事件流 (EventBus)

```
Data Fetcher → EventBus.publish(topic, payload)
                    │
                    ▼
        ┌───────────────────────┐
        │   asyncio Queue       │
        │   (topic → queue 映射) │
        └───────────────────────┘
                    │
        ┌───────────┼───────────┬──────────────┐
        ▼           ▼           ▼              ▼
   Signal      WebSocket     Notifier     Database
   Pipeline    Broadcast     Trigger      Writer
```

**Topics**:
- `GEXMETRIX_SNAPSHOT` — 新 GEXMetrix 快照
- `SIGNAL` — 共振信号触发
- `INCIDENT` — LEVEL_3 告警事件
- `CONFIG` — 配置变更广播

### 2.4 目录结构

```
Multi-source-Resonance/
├── api_server.py              # FastAPI 主入口 (48+ 路由)
├── main_scheduler.py          # APScheduler 任务编排
├── main_stream.py             # EventBus 流式入口
├── run_pipeline_v2.py         # Pipeline V2.0 执行器
├── check_status.py            # 健康检查脚本
├── config/
│   ├── settings.py            # 配置管理 (Config 类)
│   └── .env.example           # 环境变量模板
├── data_fetchers/             # 数据采集层 (14 个 fetcher/adapter)
│   ├── gexmetrix_fetcher.py   # GEXMetrix API (含 parse_strikes)
│   ├── squeezemetrics_fetcher.py
│   ├── hyperliquid_fetcher.py # 加密衍生品 (主)
│   ├── ccdata_fetcher.py      # CCData (降级)
│   ├── yahoo_finance_fetcher.py
│   ├── tradier_fetcher.py
│   ├── finra_fetcher.py
│   ├── axlfi_fetcher.py       # AXLFI 暗盘净头寸
│   ├── dbmf_fetcher.py        # DBMF 均线
│   ├── stockgrid_fetcher.py   # StockGrid
│   ├── coinglass_fetcher.py   # Coinglass
│   ├── monitor.py             # 采集监控
│   └── source_status.py       # 数据源状态模型
├── data_stream/               # 实时流层
│   ├── event_bus.py           # asyncio pub/sub (269 行)
│   ├── signal_pipeline.py     # 信号管道 (766 行)
│   ├── rest_poll_scheduler.py # 主调度器 (934 行)
│   ├── stream_engine.py       # 流引擎
│   └── pipeline_monitor.py    # 管道监控
├── database/
│   ├── db_manager.py          # SQLite ORM (11 表 + 5 视图)
│   ├── schema.sql             # DDL
│   ├── clickhouse_client.py   # ClickHouse (可选)
│   ├── clickhouse_schema.sql
│   └── monitoring.db          # SQLite 数据库
├── quant_logic/               # 量化逻辑层
│   ├── gex_calculator.py      # GEX 计算 (1171 行)
│   ├── bs_engine.py           # BS 引擎 (438 行)
│   ├── vix_analyzer.py        # VIX 分析
│   ├── cross_asset.py         # 跨资产共振 (509 行)
│   ├── vex_calculator.py      # Vanna Exposure
│   ├── svi_calibrator.py      # SVI 波动率曲面
│   ├── alpha_calibrator.py    # alpha 校准
│   ├── darkpool_verifier.py   # 暗盘验证
│   ├── darkpool_preprocessor.py
│   ├── crypto_leverage_cleaner.py
│   ├── fast_vollib_engine.py  # fast-vollib 加速
│   ├── gex_data_quality.py    # 数据质量
│   ├── dimension_reducer.py   # 多因子降维
│   └── data_validator.py      # 数据校验
├── signal_engine/             # 信号引擎
│   ├── resonance_scorer.py    # 四维评分 (870 行)
│   └── signal_trigger.py      # 状态机 (528 行)
├── gateway/                   # Layer2 网关
│   ├── schemas.py             # Pydantic 契约 (277 行)
│   ├── validator.py           # 校验器 (346 行)
│   ├── serializer.py          # 序列化 + 脱敏 (214 行)
│   └── interceptor.py         # 三级拦截 (376 行)
├── pipeline_v2/               # Pipeline V2.0
│   ├── orchestrator.py        # 六阶段编排 (850 行)
│   └── monitor.py             # 阶段监控
├── llm_inference/             # Layer3 LLM 推理
│   ├── base.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── prompt_builder.py
│   ├── response_parser.py
│   └── report_composer.py
├── backtest_engine/           # 回测引擎
│   ├── signal_replay.py       # 信号回放 (294 行)
│   ├── performance.py         # 绩效计算 (223 行)
│   └── report.py              # 报告生成
├── notification/
│   └── alert_sender.py        # 多渠道告警
├── data/                      # 运行时数据
│   ├── snapshot_recorder.py   # V3.1 快照记录器
│   ├── signal_state.json      # 信号状态持久化
│   ├── raw/                   # 原始数据
│   └── snapshots/             # 快照文件
├── frontend/                  # React + Vite 前端
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx            # 路由配置
│   │   ├── index.css          # V3.0 设计令牌 (475 行)
│   │   ├── pages/             # 9 个页面
│   │   ├── components/        # 18 个组件 (含 V3.0/V3.1)
│   │   ├── stores/            # 4 个 Zustand store
│   │   ├── hooks/             # 自定义 hooks
│   │   ├── api/               # 15 个 API 模块 (含 snapshots.ts)
│   │   ├── types/             # TS 类型定义
│   │   └── utils/             # 工具函数
│   ├── dist/                  # 构建产物
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── deploy/                    # 部署配置
│   ├── setup.sh / setup.ps1   # 一键部署
│   ├── multi-resonance.service
│   ├── nginx.conf
│   ├── prometheus.yml
│   └── pipeline_v2.cron
├── scripts/
│   └── backfill_gex_history.py # 90 天 SqueezeMetrics 回填
├── tests/
├── Dockerfile                 # 多阶段构建
├── docker-compose.yml
├── requirements.txt
└── README.md                  # 本文档
```

### 2.5 实际代码目录结构 (v3.1)

> **说明**: 上述 2.4 节展示的是原始设计逻辑结构。实际代码已统一重构到 `backend/` 子目录下，以下是**实际代码**与**原设计**的映射关系。

```
Multi-source-Resonance/
├── backend/                       # 后端代码根目录
│   ├── main.py                    # FastAPI 应用入口 (uvicorn 启动)
│   ├── config.py                  # 配置管理 (Settings 类, 环境变量)
│   ├── database.py                # SQLite async ORM (11 表 + 5 视图, aiosqlite)
│   ├── api/                       # REST API 层
│   │   ├── middleware/
│   │   │   ├── auth.py            # JWT 鉴权中间件 (写端点保护)
│   │   │   └── rate_limit.py      # API 限流 (slowapi, 100/min)
│   │   ├── routes/                # 路由模块 (10 个蓝图)
│   │   │   ├── auth.py            #   认证 (login/refresh/logout)
│   │   │   ├── dashboard.py       #   仪表盘聚合
│   │   │   ├── gex.py             #   GEX 元数据
│   │   │   ├── vix.py             #   VIX 期限结构
│   │   │   ├── darkpool.py        #   暗池指标
│   │   │   ├── crypto.py          #   加密衍生品
│   │   │   ├── signals.py         #   信号 & 告警
│   │   │   ├── config.py          #   配置管理
│   │   │   ├── system.py          #   系统 & 采集触发
│   │   │   ├── metrics.py         #   Prometheus 指标
│   │   │   └── analysis.py        #   LLM 分析
│   │   └── websocket.py           # WebSocket 管理
│   ├── fetchers/                  # 数据采集层 → 对应原设计 data_fetchers/
│   │   ├── base.py                #   Fetcher 基类
│   │   ├── base_alt.py            #   备选基类
│   │   ├── gexmetrix_fetcher.py   #   GEXMetrix API
│   │   ├── yfinance_fetcher.py    #   yfinance OHLCV
│   │   ├── vix_fetcher.py         #   CBOE VIX
│   │   ├── vix_term_fetcher.py    #   VIX 期限结构
│   │   ├── darkpool_fetcher.py    #   暗池 DIX
│   │   ├── crypto_fetcher.py      #   加密衍生品 (Hyperliquid→CCData)
│   │   ├── axlfi_fetcher.py       #   AXLFI 暗盘净头寸
│   │   ├── macro_fetcher.py       #   宏观数据
│   │   ├── sector_fetcher.py      #   板块数据
│   │   ├── flow_fetcher.py        #   资金流
│   │   ├── put_call_fetcher.py    #   Put/Call 比率
│   │   ├── sentiment_fetcher.py   #   情绪指标
│   │   ├── llm_fetcher.py         #   LLM 推理 (OpenAI→Anthropic→模板)
│   │   └── cboe_fetcher.py        #   CBOE 数据
│   ├── quant/                     # 量化逻辑层 → 对应原设计 quant_logic/
│   │   ├── scoring.py             #   四维共振评分
│   │   ├── gex_analyzer.py        #   GEX 分析
│   │   ├── vix_analyzer.py        #   VIX 分析
│   │   ├── vix_term_analyzer.py   #   VIX 期限结构分析
│   │   ├── crypto_analyzer.py     #   加密衍生品分析
│   │   ├── darkpool_analyzer.py   #   暗池分析
│   │   ├── flow_analyzer.py       #   资金流分析
│   │   ├── macro_analyzer.py      #   宏观分析
│   │   ├── sector_analyzer.py     #   板块分析
│   │   ├── put_call_analyzer.py   #   Put/Call 分析
│   │   ├── sentiment_analyzer.py  #   情绪分析
│   │   ├── bayesian_weights.py    #   贝叶斯权重自适应
│   │   ├── hawkes_model.py        #   Hawkes 自激模型
│   │   ├── llm_analyzer.py        #   LLM 分析器
│   │   ├── llm_cache.py           #   LLM 推理缓存 (SHA-256 + SQLite)
│   │   └── backtest_engine.py     #   回测引擎 (Walk-forward + 敏感性)
│   ├── models/                    # Pydantic 数据模型 → 对应原设计 gateway/
│   │   ├── common.py              #   通用模型
│   │   ├── signal.py              #   信号模型
│   │   ├── gex.py                 #   GEX 模型
│   │   ├── vix.py                 #   VIX 模型
│   │   ├── darkpool.py            #   暗池模型
│   │   ├── crypto.py              #   加密模型
│   │   └── system.py              #   系统模型
│   ├── eventbus/                  # 事件总线 → 对应原设计 data_stream/event_bus
│   │   ├── event_bus.py           #   asyncio pub/sub
│   │   └── events.py              #   事件定义
│   ├── pipeline/                  # 数据流水线 → 对应原设计 data_stream/pipeline
│   │   ├── pipeline.py            #   主流水线
│   │   ├── concurrent_executor.py #   并发执行器
│   │   └── data_writer.py         #   数据写入器
│   ├── notifications/             # 通知推送 → 对应原设计 notification/
│   │   └── notifier.py            #   多渠道告警 (Email/Telegram/Discord)
│   ├── utils/                     # 工具模块
│   │   ├── scheduler.py           #   APScheduler 任务编排
│   │   ├── security.py            #   密码哈希/验证
│   │   ├── db_maintenance.py      #   数据库维护 (VACUUM/归档/备份)
│   │   └── structured_logging.py  #   structlog 结构化日志
│   └── tests/                     # 测试套件
│       ├── unit/                  #   单元测试
│       ├── integration/           #   集成测试
│       └── conftest.py            #   pytest 配置
├── frontend/                      # React + Vite 前端 (与 2.4 一致)
├── data/                          # 运行时数据
│   ├── resonance.db               #   SQLite 数据库 (WAL)
│   ├── resonance.db-shm
│   └── resonance.db-wal
├── deploy/                        # 部署配置
│   ├── grafana_dashboard.json     #   Grafana 仪表盘
│   └── prometheus_rules.yml       #   Prometheus 告警规则
├── scripts/
│   └── db_backup.sh               #   数据库备份脚本 (全量/增量)
├── docs/                          # 文档
├── requirements.txt
├── pyproject.toml
└── README.md
```

#### 路径映射对照表

| 原设计路径 | 实际代码路径 | 说明 |
|------------|-------------|------|
| `data_fetchers/` | `backend/fetchers/` | 14 个 fetcher 统一在此 |
| `quant_logic/` | `backend/quant/` | 量化分析 + 评分 + 回测 |
| `data_stream/event_bus.py` | `backend/eventbus/event_bus.py` | asyncio pub/sub |
| `data_stream/signal_pipeline.py` | `backend/pipeline/pipeline.py` | 主流水线 |
| `data_stream/rest_poll_scheduler.py` | `backend/utils/scheduler.py` | 任务编排 |
| `gateway/` (schemas, validator) | `backend/models/` | Pydantic 数据模型 |
| `signal_engine/` | `backend/quant/scoring.py` | 评分逻辑合并到 quant |
| `llm_inference/` | `backend/quant/llm_analyzer.py` + `backend/fetchers/llm_fetcher.py` | LLM 推理拆分到 quant 和 fetchers |
| `backtest_engine/` | `backend/quant/backtest_engine.py` | 独立回测引擎文件 |
| `notification/` | `backend/notifications/notifier.py` | 多渠道通知 |
| `api_server.py` | `backend/main.py` | FastAPI 入口 |
| `config/settings.py` | `backend/config.py` | 配置管理 |
| `database/db_manager.py` | `backend/database.py` | 数据库层 |
| `tests/` | `backend/tests/` | 测试套件 |

---

## 3. 数据源矩阵

| 维度 | 数据源 | 频率 | 端点 | 字段 | 降级 |
|------|--------|------|------|------|------|
| **GEX (做市商 Gamma)** | GEXMetrix | 盘中/批量 | `api.gexmetrix.com/api/files/{sym}/latest` | net_gex, call_wall, put_wall, zero_gamma, options[] | SqueezeMetrics |
| **GEX 历史回填** | SqueezeMetrics | 周一 21:00 | `squeezemetrics.com/dix` | gex_local, gex_calibrated, alpha_factor, flip_zone | — |
| **暗池 / DIX** | SqueezeMetrics | 日 | 同上 | dix_value, chartexchange_short_ratio, stockgrid_slope | FINRA short_interest |
| **暗盘净头寸** | AXLFI | 日 | AXLFI API | dark_net_position, dark_volume | — |
| **做空数据** | FINRA | 双周 | `api/data/groups/shortInterest` | short_interest, days_to_cover | yfinance |
| **价格 / OHLCV** | yfinance | 实时 | `query1.finance.yahoo.com` | open/high/low/close/volume | — |
| **VIX 期限结构** | CBOE | 日 | `cdn.cboe.com/api/us/...` | vix_spot, vx1, vx2, term_structure_ratio | — |
| **加密衍生品** | Hyperliquid | 实时 | `api.hyperliquid.xyz/info` | btc_funding, btc_oi, oi_change, liquidation_spike | CCData (需 Key) |
| **DBMF 均线** | DBMF ETF | 日 | DBMF API | dbmf_value, ma5, ma20, ma5_recovery | — |

---

## 4. 数据架构

### 4.1 数据库概览

**SQLite 11 张表，按业务域分组**:

```
┌─────────────────────────────────────────────────────────────────┐
│  GEX 域 (4 表)                                                  │
│  ├─ gex_snapshots         — GEXMetrix 最新快照摘要(17 列,90 行)│
│  ├─ gex_strikes           — 逐 strike 真实 GEX/OI(12 列,3332) │
│  ├─ gex_history           — SqueezeMetrics 日级历史(8 列,103)  │
│  └─ alpha_history         — alpha 因子历史(9 列,0 行)          │
├─────────────────────────────────────────────────────────────────┤
│  其他维度域 (4 表)                                               │
│  ├─ vix_analysis          — VIX 期限结构(9 列,7 行)            │
│  ├─ dark_pool_metrics     — 暗池 DIX/EMA(18 列,253 行)         │
│  ├─ crypto_derivatives    — 加密衍生品(10 列,26 行)            │
│  └─ system_config         — 系统配置(key-value,3 行)           │
├─────────────────────────────────────────────────────────────────┤
│  信号 & 审计域 (3 表)                                            │
│  ├─ signal_alerts         — 共振信号告警(12 列)                │
│  ├─ validation_audit_log  — 数据校验日志(14 列,0 行)           │
│  └─ gateway_snapshots     — Gateway 快照(10 列,0 行)           │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 核心表 schema

#### `gex_snapshots` — GEXMetrix 摘要

```sql
CREATE TABLE gex_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,        -- SPX/SPY/QQQ/IWM/NDX/VIX
    timestamp       DATETIME NOT NULL,
    filename        TEXT NOT NULL,        -- 原始 JSON 文件名
    net_gex         REAL,                 -- 净 Gamma Exposure
    call_gex        REAL,                 -- Call 端 GEX 总和
    put_gex         REAL,                 -- Put 端 GEX 总和 (负数)
    zero_gamma_level REAL,                -- 零 Gamma 价位 (做市商方向分界)
    call_wall       REAL,                 -- Call Wall (最大 Call GEX 价位)
    put_wall        REAL,                 -- Put Wall (最大 Put GEX 价位)
    spot_price      REAL,                 -- 标的现价
    total_gamma     REAL,                 -- Gamma 总和 (|call_gex| + |put_gex|)
    file_size       INTEGER,              -- 原始 JSON 字节数
    created_at      DATETIME,
    quality_score   REAL,                 -- 数据质量分 (0-1)
    data_lag_seconds INTEGER,             -- 数据延迟 (秒)
    oi_coverage_pct REAL                  -- OI 覆盖率 (0-100)
);
CREATE INDEX idx_gex_snapshots_sym_ts ON gex_snapshots (symbol, timestamp DESC);
```

#### `gex_strikes` — 逐 strike 真实分布(V2.5 新增)

```sql
CREATE TABLE gex_strikes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,         -- FK → gex_snapshots.id
    symbol      TEXT NOT NULL,
    timestamp   DATETIME NOT NULL,
    strike      REAL NOT NULL,            -- 行权价
    call_gex    REAL NOT NULL DEFAULT 0,  -- 该 strike Call GEX ($)
    put_gex     REAL NOT NULL DEFAULT 0,  -- 该 strike Put GEX ($)
    call_oi     INTEGER NOT NULL DEFAULT 0,
    put_oi      INTEGER NOT NULL DEFAULT 0,
    call_vol    INTEGER NOT NULL DEFAULT 0,
    put_vol     INTEGER NOT NULL DEFAULT 0,
    net_gex     REAL NOT NULL DEFAULT 0,  -- = call_gex + put_gex (put 已负方向)
    FOREIGN KEY (snapshot_id) REFERENCES gex_snapshots(id) ON DELETE CASCADE
);
CREATE INDEX idx_gex_strikes_sym_ts ON gex_strikes (symbol, timestamp DESC);
CREATE INDEX idx_gex_strikes_snap ON gex_strikes (snapshot_id);
```

**GEX 聚合公式** (在 `gexmetrix_fetcher.py:parse_strikes`):
```python
gex_value = gamma * oi * multiplier * spot * spot * 0.01
# SPY/QQQ/IWM: multiplier=100
# SPX 指数期权: multiplier=100
# 默认 min_oi=100 过滤深度虚值
```

#### `gex_history` — SqueezeMetrics 90 天回填

```sql
CREATE TABLE gex_history (
    timestamp          DATETIME PRIMARY KEY,
    gex_local          REAL NOT NULL,       -- 局部 GEX
    gex_calibrated     REAL,                -- 校准 GEX (相对标尺)
    alpha_factor       REAL,                -- 校准系数 (系统配置,默认 1.0)
    put_wall_level     REAL,                -- Put Wall 价位
    flip_zone_lower    REAL,                -- GEX 翻转区间下沿
    flip_zone_upper    REAL,                -- GEX 翻转区间上沿
    created_at         DATETIME
);
```

#### `vix_analysis` — VIX 期限结构

```sql
CREATE TABLE vix_analysis (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    vix_spot              REAL,              -- VIX 即期
    vx1                   REAL,              -- VIX 1 月期货
    vx2                   REAL,              -- VIX 2 月期货
    term_structure_ratio  REAL,              -- (vx2/vx1) - 1
    term_structure_state  TEXT,              -- 'contango' | 'backwardation' | 'flat'
    panic_premium         REAL,              -- 恐慌溢价
    created_at            DATETIME
);
```

#### `dark_pool_metrics` — 暗池 / DIX

```sql
CREATE TABLE dark_pool_metrics (
    date                       DATE PRIMARY KEY,
    dix_value                  REAL,            -- Dark Index (DIX) 暗池交易占比
    chartexchange_short_ratio  REAL,            -- ChartExchange 做空比例
    stockgrid_20d_slope        REAL,            -- 20 日价格斜率
    stockgrid_60d_slope        REAL,            -- 60 日价格斜率
    stockgrid_divergence       BOOLEAN,         -- 价/量背离
    dbmf_ma5_recovery          BOOLEAN,         -- MA5 反弹
    dix_signal                 BOOLEAN,
    short_ratio_signal         BOOLEAN,
    stockgrid_signal           BOOLEAN,
    aggregated_signal          BOOLEAN,
    v_net                      REAL,            -- 净做空量
    ema_fast_5                 REAL,            -- EMA 5 日 (V_Net)
    ema_slow_20                REAL,            -- EMA 20 日
    zero_cross_signal          TEXT,            -- 'bullish_cross' | 'bearish_cross'
    momentum_reversal_signal   TEXT,
    created_at                 DATETIME,
    updated_at                 DATETIME
);
```

#### `crypto_derivatives` — 加密衍生品

```sql
CREATE TABLE crypto_derivatives (
    timestamp          DATETIME PRIMARY KEY,
    btc_funding_rate   REAL NOT NULL,
    btc_oi             REAL,                -- Open Interest (BTC)
    oi_change_1h       REAL,                -- 1 小时 OI 变化率
    liquidation_spike  BOOLEAN,
    cryptoquant_elr    REAL,                -- Estimated Leverage Ratio
    funding_anomaly    BOOLEAN,
    oi_crash           BOOLEAN,
    leverage_cleanup   BOOLEAN,             -- 杠杆清洗信号 (抄底关键信号之一)
    created_at         DATETIME
);
```

#### `signal_alerts` — 共振信号告警

```sql
CREATE TABLE signal_alerts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_time            DATETIME NOT NULL,
    total_score             REAL NOT NULL,    -- 共振总分 (0-5.0)
    gex_score               REAL,             -- GEX 维度贡献 (0-1.5)
    vix_score               REAL,             -- VIX 维度贡献
    crypto_score            REAL,
    darkpool_score          REAL,
    alert_level             TEXT NOT NULL,    -- 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3'
    hawkes_branching_ratio  REAL,             -- Hawkes 自激分支比
    details                 TEXT,             -- JSON 详情
    acknowledged            BOOLEAN,
    created_at              DATETIME
);
```

#### `system_config` — 系统配置

```sql
CREATE TABLE system_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  DATETIME
);
-- 当前值:
--   'alpha_factor' = '1.0'        (GEX 校准系数)
--   'gex_threshold' = '35000000'   (GEX 阈值 35M)
--   'alert_level_3_min' = '3.5'    (LEVEL_3 最低分)
```

### 4.3 ER 图(逻辑关系)

```
gex_snapshots 1 ──< gex_strikes   (一对多, 同一 snapshot 数百 strikes)
gex_snapshots 1 ──1 signal_alerts (一次 snapshot 可触发零或一信号)
dark_pool_metrics ──< signal_alerts (作为 darkpool_score 输入)
vix_analysis ──< signal_alerts
crypto_derivatives ──< signal_alerts
gex_history (SqueezeMetrics) ──< gex_snapshots (作为回填基线)
system_config (key-value) ── 全局参数
```

### 4.4 数据流时序

```
Daily Batch (美东 20:00):
  1. RESTPollScheduler → 拉取所有数据源
  2. 原始 JSON → data/gexmetrix/{sym}/{ts}.json (缓存)
  3. parse_snapshot_key_metrics → gex_snapshots
  4. parse_strikes (V2.5) → gex_strikes
  5. EventBus.publish('GEXMETRIX_SNAPSHOT', {snapshots, strikes})
  6. Signal Pipeline 监听 → 计算四维评分
  7. 触发 LEVEL_3 → signal_alerts + Notifier
  8. 自动记录快照 → data/snapshots/ (V3.1, 5 分钟节流)

Manual Trigger (POST /api/system/collect-manual):
  同上流程, 8 数据维度并发 (总耗时 ~10s)
```

---

## 5. API 接口文档

**Base URL**: `http://0.0.0.0:8524`
**CORS**: 允许 `http://localhost:8524`、`http://127.0.0.1:8524`
**响应格式**: 全部 `application/json`

### 5.1 健康 & 系统

| 方法 | 路径 | 说明 | 返回 |
|------|------|------|------|
| `GET` | `/api/health` | 健康检查 | `{status, timestamp, version, uptime_seconds}` |
| `GET` | `/api/status` | 系统状态 (CPU/内存/连接数) | 系统指标 |
| `GET` | `/api/metrics` | Prometheus 风格指标 | 文本 |
| `GET` | `/api/system/source-status` | 8 数据源连通性 | `[{name, status, method, availability_pct, last_error}]` |
| `GET` | `/api/system/logs/stream` | 实时日志流 (SSE) | SSE 流 |
| `GET` | `/api/system/auto-polling` | 当前自动轮询状态 | `{enabled, schedule}` |
| `PUT` | `/api/system/auto-polling` | 切换自动轮询 | 同上 |

### 5.2 仪表盘聚合

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/dashboard/scores` | 当前四维共振评分 (自动记录快照) |
| `GET` | `/api/dashboard/recent-alerts` | 最近告警 |
| `GET` | `/api/dashboard/resonance-history` | 共振分数历史 |
| `GET` | `/api/dashboard/cross-asset-heatmap` | 跨资产热力图 |
| `GET` | `/api/dashboard/gex-curve?days=N` | GEX 长期曲线(SqueezeMetrics)，默认 90 天 |
| `GET` | `/api/dashboard/multi-channel-curve` | 三通道 (GEX+VEX+CHEX) 曲线 (V2.5) |
| `GET` | `/api/dashboard/data-quality` | 流动性门控质量评分 |
| `GET` | `/api/dashboard/pipeline-metrics` | Pipeline V2.0 运行指标 |

### 5.3 GEX 元数据 (V2.5)

| 方法 | 路径 | Query | 说明 |
|------|------|-------|------|
| `GET` | `/api/gex/symbols` | — | 所有可用标的 + 新鲜度 |
| `GET` | `/api/gex/summary` | — | 6 标的最新摘要 (one-shot) |
| `GET` | `/api/gex/history` | `days=N` (默认 90) | SqueezeMetrics 90 天历史 |
| `GET` | `/api/gex/{symbol}/latest` | — | GEXMetrix 最新快照摘要 |
| `GET` | `/api/gex/{symbol}/history` | `days=N` | GEXMetrix 时间序列 (≤3 天) |
| `GET` | `/api/gex/{symbol}/levels` | — | 关键价位 (call_wall / put_wall / zero_gamma) |
| `GET` | `/api/gex/{symbol}/strikes` | `limit=N` (默认 200, 最大 600) | 逐 strike 真实 GEX/OI 分布 |
| `GET` | `/api/gex/{symbol}/dashboard-view` | `history_days=3&long_days=90&strikes_limit=200` | **BFF 聚合接口** |

#### `/api/gex/{symbol}/dashboard-view` — BFF 聚合

**V2.5 新增**。单次调用返回 6 个 section，替代前端 6 个独立 `useQuery`，消除 waterfall。

**Query 参数**:
- `history_days`: GEXMetrix 短期窗口 (1-7, 默认 3)
- `long_days`: SqueezeMetrics 长期窗口 (30-365, 默认 90)
- `strikes_limit`: ATM 附近 strike 数量 (10-600, 默认 200)

**响应**:
```json
{
  "symbol": "SPX",
  "fetched_at": "2026-07-28T05:49:51.26",
  "latest": {
    "id": 93,
    "symbol": "SPX",
    "timestamp": "2026-07-28T05:49:50.87",
    "filename": "20260726_204522.json",
    "net_gex": -312694.56,
    "call_gex": 1120000000,
    "put_gex": -1432694456,
    "zero_gamma_level": 6950.0,
    "call_wall": 7000.0,
    "put_wall": 7000.0,
    "spot_price": 7354.02,
    "total_gamma": 2552694456,
    "file_size": 15435364,
    "quality_score": 0.95,
    "data_lag_seconds": 60,
    "oi_coverage_pct": 98.5
  },
  "levels": {
    "call_wall": 7000.0,
    "put_wall": 7000.0,
    "zero_gamma_level": 6950.0,
    "spot_price": 7354.02,
    "net_gex": -312694.56,
    "call_gex": 1120000000,
    "put_gex": -1432694456
  },
  "history": [
    {"symbol": "SPX", "timestamp": "2026-07-25T...", "net_gex": ..., "spot_price": ...},
    ...14 条
  ],
  "long_history": [
    {"timestamp": "2026-04-30T16:00:00", "gex_local": -1500000, "gex_calibrated": -1500000,
     "alpha_factor": 1.0, "put_wall_level": 6900.0, "flip_zone_lower": 6950, "flip_zone_upper": 7050},
    ...73 条
  ],
  "strikes": {
    "timestamp": "2026-07-28T05:49:50.87",
    "spot_price": 7354.02,
    "strike_count": 200,
    "strikes": [
      {"strike": 7330.0, "call_gex": 105490000, "put_gex": -565670000,
       "call_oi": 12345, "put_oi": 23456, "call_vol": 5678, "put_vol": 6789,
       "net_gex": -460180000},
      ...
    ]
  },
  "symbols": [
    {"symbol": "SPX", "latest_timestamp": "...", "snapshot_count": 6, "age_minutes": 0.5},
    {"symbol": "SPY", ...},
    ...
  ]
}
```

**性能**: 7.3ms (含 200 strikes)，替代 6 个独立调用。

### 5.4 VIX / 暗池 / 标的

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/vix/history?days=N` | VIX 期限结构历史 |
| `GET` | `/api/darkpool/history?days=N` | 暗池指标历史 |
| `GET` | `/api/tickers` | 可监控标的列表 |

### 5.5 信号 & 告警

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/signals/current` | 当前活跃信号 |
| `GET` | `/api/signals/history` | 历史信号 |
| `POST` | `/api/signals/{id}/acknowledge` | 确认信号 |
| `GET` | `/api/alerts` | 告警列表 |
| `POST` | `/api/alerts/{id}/acknowledge` | 确认告警 |
| `GET` | `/api/incidents` | Incident 列表(LEVEL_3 告警事件) |
| `GET` | `/api/incidents/{id}` | Incident 详情 |
| `PUT` | `/api/incidents/{id}/review` | 标记已复盘 |
| `GET` | `/api/incidents/{id}/export` | 导出 JSON 报告 |

### 5.6 V3.1 快照 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/snapshots` | 快照时间线列表 (按时间倒序) |
| `GET` | `/api/snapshots/stats` | 快照统计摘要 (总数/日期范围/每日计数) |
| `GET` | `/api/snapshots/{timestamp}` | 获取指定时刻快照数据 (完整 DashboardScores) |
| `POST` | `/api/snapshots/capture` | 手动触发快照捕获 |

**自动记录**: 每次 `/api/dashboard/scores` 请求自动记录快照 (5 分钟节流)，由 `data/snapshot_recorder.py` 实现。

### 5.7 配置 & LLM

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/config` | 当前配置 |
| `GET` | `/api/config/defaults` | 默认配置 |
| `GET` | `/api/config/audit` | 配置变更审计 |
| `PUT` | `/api/config` | 更新配置(写入 system_config + audit_log) |
| `POST` | `/api/config/restore` | 还原到默认 |
| `GET` | `/api/llm/status` | LLM provider 状态 |
| `POST` | `/api/llm/analyze` | 触发 LLM 分析(signal/incident) |

### 5.8 通知 & 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/notifications/config` | 通知渠道配置 |
| `PUT` | `/api/notifications/config` | 更新通知配置 |
| `GET` | `/api/notifications/status` | 通知状态 |
| `POST` | `/api/notifications/test` | 测试通知发送 |
| `POST` | `/api/auth/login` | 登录(JWT) |

### 5.9 WebSocket

```
WS /ws
```

**消息格式**:
```json
{
  "topic": "GEXMETRIX_SNAPSHOT",
  "payload": {...},
  "timestamp": "2026-07-28T05:49:51"
}
```

**订阅方式**: 客户端连上后默认收所有 topic；前端可基于 topic 过滤。

### 5.10 手动采集

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/system/collect-manual` | **手动触发完整 8 数据维度采集循环** |

**响应示例**:
```json
{
  "ok": true,
  "collected_at": "2026-07-28T05:49:51.26",
  "total_elapsed_sec": 9.88,
  "success_count": 8,
  "sources": [
    {"name": "GEX/DIX", "status": "success", "elapsed_sec": 1.19},
    {"name": "VIX期限结构", "status": "success", "elapsed_sec": 5.02},
    {"name": "AXLFI暗盘", "status": "success", "elapsed_sec": 9.32},
    {"name": "DBMF均线", "status": "success", "elapsed_sec": 2.20},
    {"name": "加密衍生品", "status": "success", "elapsed_sec": 2.51},
    {"name": "做空数据", "status": "success", "elapsed_sec": 3.45},
    {"name": "StockGrid", "status": "success", "elapsed_sec": 4.12},
    {"name": "GEXMetrix", "status": "success", "elapsed_sec": 9.87}
  ]
}
```

---

## 6. 后端设计

### 6.1 FastAPI 启动流程

```python
# api_server.py 启动序列

4. EventBus()                  # asyncio 队列
5. RESTPollScheduler()        # 启动 APScheduler
6. WebSocketManager()          # 管理 WS 连接
7. Mount StaticFiles           # / → dist/
8. uvicorn.run(host='0.0.0.0', port=8524)
```

### 6.2 异步并发模型

**采集并发** (`rest_poll_scheduler.py:_collect_all_sources`):
```python
async def collect_all_sources(self):
    tasks = [
        asyncio.create_task(self._poll_gexmetrix_once()),
        asyncio.create_task(self._poll_squeezemetrics_once()),
        asyncio.create_task(self._poll_vix_once()),
        asyncio.create_task(self._poll_darkpool_once()),
        asyncio.create_task(self._poll_short_interest_once()),
        asyncio.create_task(self._poll_crypto_once()),
        asyncio.create_task(self._poll_axlfi_once()),
        asyncio.create_task(self._poll_dbmf_once()),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 单源失败不影响整体
```

**线程池**: CPU 密集任务(`parse_strikes`, `parse_snapshot_key_metrics`)通过 `loop.run_in_executor(self._executor, fn)` 提交到 ThreadPoolExecutor，避免阻塞 event loop。

**EventBus 实现** (`data_stream/event_bus.py`):
```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = {}

    async def publish(self, topic: str, payload: dict):
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue()
        await self._queues[topic].put(payload)
        # asyncio.create_task 异步分发

    def subscribe(self, topic: str, handler: Callable):
        self._subscribers[topic].append(handler)
```

### 6.3 信号流水线 (V2.0)

```
GEXMetrix Snapshot
   |
   v
[Layer1: math]
   - 解析 options[] -> 逐 strike 聚合
   - 计算 Call Wall / Put Wall / Zero Gamma
   - 计算 Net GEX, Total Gamma
   - 输出: Dict[str, float]
   |
   v
[Layer2: gateway]
   - 序列化 Layer1 输出为标准 JSON
   - 注入上下文 (timestamp, symbol, source)
   - 触发评分逻辑 (gex_score, vix_score, ...)
   - 输出: SignalEvent (dataclass)
   |
   v
[Score Aggregation]
   - total_score = sum(dim_score * weight)
   - alert_level = level(total_score)
   - Hawkes AR(1) 分支比计算
   |
   v
[Layer3: LLM]
   - 接收 Layer2 JSON
   - 调 GPT-4o / Claude 生成报告
   - 失败降级到模板
   |
   v
[Notifier + DB Writer]
   - 写入 signal_alerts
   - 触发 Email / Telegram / Discord
   - 自动记录快照 (V3.1, 5 分钟节流)
```

### 6.4 四维评分逻辑

```python
# signal_engine/resonance_scorer.py
GEX_WEIGHTS = {
    "net_gex_positive": 1.50,        # GEX 转正 (做市商反转)
    "zero_gamma_above_spot": 0.50,   # Spot < Zero Gamma (多 GEX 区域)
    "call_wall_proximity": 0.50,     # 接近 Call Wall
}
VIX_WEIGHTS = {
    "term_structure_contango": 1.00, # 期限结构正挂 (恐慌缓解)
    "panic_premium_low": 0.50,
}
CRYPTO_WEIGHTS = {
    "leverage_cleanup": 1.00,        # 杠杆清洗 (抄底关键)
    "funding_anomaly": 0.50,
    "oi_crash": 0.50,
}
DARKPOOL_WEIGHTS = {
    "dix_bullish": 1.00,
    "short_ratio_extreme": 0.50,
    "momentum_reversal": 0.50,
}

# LEVEL 阈值 (signal_alerts.alert_level)
LEVEL_THRESHOLDS = {
    "LEVEL_1": 2.0,   # 观察
    "LEVEL_2": 3.0,   # 关注
    "LEVEL_3": 3.5,   # 强信号 + 推送
}
```

### 6.5 降级容错

```python
# data_fetchers/crypto_fetcher.py
class CryptoFetcher:
    PRIMARY = "hyperliquid"
    FALLBACK = "ccdata"

    async def fetch(self):
        try:
            return await self._fetch_hyperliquid()
        except Exception as e:
            logger.warning(f"Hyperliquid failed: {e}, fallback to CCData")
            return await self._fetch_ccdata()
```

**降级链**:
- Crypto: Hyperliquid -> CCData (需 Key) -> 返回空 + 标记 OFFLINE
- Short Interest: FINRA -> yfinance (估算)
- GEX: GEXMetrix -> SqueezeMetrics (无逐 strike，只有日级)

### 6.6 数据校验防线 (Phase 4)

```python
# gateway/validator.py
class DataValidator:
    checks = [
        GreeksBoundsCheck(),       # gamma in [-5, 5]
        PutCallParityCheck(),      # C - P ~= S - K*exp(-rT)
        ArbitrageFreeCheck(),      # 无套利机会
        IsolationForestOutlier(),  # ML 异常检测
        PanderaSchemaCheck(),      # 列级 schema
    ]
```

**校验日志** 写入 `validation_audit_log` 表，可追溯每条数据的校验失败原因。

---

## 7. 前端设计

### 7.1 技术栈

| 层 | 技术 | 版本 | 用途 |
|----|------|------|------|
| 构建 | Vite | 8.0 | 极速 HMR + 构建 |
| UI 框架 | React | 18.3 | 函数组件 + Hooks |
| 路由 | React Router | 7.17 | 客户端路由 |
| 数据 | TanStack Query | 5 | 服务端状态缓存 |
| 状态 | Zustand | 5.0 | 客户端状态 (auth, theme, timezone, staleness) |
| 图表 | ECharts (echarts-for-react) | 6.1 | 自定义 resonance-v3 主题 |
| CSS | Tailwind CSS | 4.3 | + CSS 变量设计令牌 (V3.0) |
| HTTP | fetch + 自定义 client | - | API 调用 |
| 类型 | TypeScript | 6.0 | 全量类型检查 |

### 7.2 目录结构

```
frontend/src/
├── main.tsx               # 入口 (路由 + QueryClient)
├── App.tsx                # 路由配置
├── index.css              # V3.0 设计令牌 (475 行)
├── pages/                 # 9 个页面 (路由目标)
│   ├── Dashboard.tsx      # 主仪表盘 (四维评分 + V3.1 回放控制)
│   ├── GammaDashboard.tsx # Gamma 深度仪表盘 (V2.5 重写)
│   ├── SignalsPanel.tsx   # Regime Transition 信号列表
│   ├── AlertCenter.tsx    # 告警中心
│   ├── SystemStatus.tsx   # 系统状态
│   ├── ConfigPanel.tsx    # 配置管理
│   ├── LLMAnalysis.tsx    # LLM 推理报告
│   ├── DarkpoolDetail.tsx # 暗池详细
│   └── LoginPage.tsx      # 登录
├── components/            # 18 个复用组件
│   ├── Layout.tsx         # 框架布局
│   ├── GlassCard.tsx      # V3.0 玻璃拟态卡片
│   ├── LiveTape.tsx       # V3.0 实时数据纸带
│   ├── TimelineReplay.tsx # V3.1 时间线回放控制
│   ├── SnapshotGallery.tsx# V3.1 快照画廊
│   ├── GEXCurveChart.tsx  # GEX 时间序列
│   ├── StrikeGexChart.tsx # 逐 Strike GEX/OI 分布
│   ├── MultiChannelChart.tsx # 三通道 (GEX+VEX+CHEX) 叠加
│   ├── NetGexHistoryChart.tsx # Net GEX 历史面积图
│   ├── HistoricalTrend.tsx
│   ├── DimensionCard.tsx  # 四维卡片
│   ├── ResonanceGauge.tsx # 共振仪表盘
│   ├── CrossAssetHeatmap.tsx
│   ├── Sparkline.tsx
│   ├── DataQualityBadge.tsx # 数据质量徽章
│   ├── DrillDownModal.tsx   # 下钻详情
│   ├── PipelineMonitorPanel.tsx # Pipeline 监控
│   └── CountUp.tsx          # 数字动画
├── api/                   # 15 个 API 模块
│   ├── client.ts          # fetch 封装 (get/post)
│   ├── gexmetrix.ts       # useGEXLatest/History/Levels/Strikes/DashboardView
│   ├── gex.ts
│   ├── dashboard.ts
│   ├── signals.ts
│   ├── alerts.ts
│   ├── incidents.ts
│   ├── snapshots.ts       # V3.1 快照 API
│   ├── config.ts
│   ├── llm.ts
│   ├── notifications.ts
│   ├── darkpool.ts
│   ├── vix.ts
│   ├── system.ts
│   ├── auth.ts
│   └── tickers.ts
├── stores/                # Zustand stores
│   ├── authStore.ts       # JWT token + 用户
│   ├── themeStore.ts      # 双主题切换 (Dark/Light) V3.0
│   ├── timezoneStore.ts   # 时区偏好
│   └── stalenessStore.ts  # 数据新鲜度
├── hooks/
│   ├── useWebSocket.ts    # WS 长连接 + 订阅
│   └── useStaleness.ts    # 数据新鲜度计算
├── types/
│   └── api.ts             # 共享 TS 类型
└── utils/                 # 工具函数
```

### 7.3 路由表

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | LoginPage | JWT 登录 |
| `/` | Dashboard | 主仪表盘 (四维评分 + V3.1 回放控制) |
| `/gex` | GammaDashboard | **Gamma 深度仪表盘 (V2.5 优化)** |
| `/signals` | SignalsPanel | Regime Transition 信号列表 |
| `/alerts` | AlertCenter | 告警中心 |
| `/status` | SystemStatus | 系统状态 |
| `/config` | ConfigPanel | 配置管理 |
| `/llm` | LLMAnalysis | LLM 推理 |
| `/darkpool` | DarkpoolDetail | 暗池详细 |

### 7.4 TanStack Query 模式 (V2.5)

**单一 hook 模式**:
```typescript
// frontend/src/api/gexmetrix.ts
export function useGEXDashboardView(
  symbol: string | null,
  options?: { history_days?: number; long_days?: number; strikes_limit?: number }
) {
  return useQuery<GEXDashboardView>({
    queryKey: ['gexmetrix', 'dashboard-view', symbol, params],
    queryFn: () => get<GEXDashboardView>(`/gex/${symbol}/dashboard-view?${params}`),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,           // 5 分钟缓存
    refetchInterval: symbol ? 5 * 60 * 1000 : false,
  })
}
```

**特性**:
- `staleTime: 5min` — 避免窗口聚焦时多余请求
- `refetchInterval: 5min` — 自动轮询
- `queryKey` 包含 params — 不同参数独立缓存
- `enabled: !!symbol` — 标的未选时不发请求

**BFF 优先策略**:
```typescript
// GammaDashboard.tsx
const bffResp = useGEXDashboardView(selectedSymbol, { history_days: 3, long_days: 90 })
const bffView = bffResp.data

const strikesData = useMemo(() => {
  const bffStrikes = bffView?.strikes?.strikes
  const hookStrikes = strikesResp?.strikes
  const realStrikes = bffStrikes?.length > 0 ? bffStrikes : hookStrikes?.length > 0 ? hookStrikes : null

  if (realStrikes) {
    return { strikes: realStrikes, isReal: true, source: 'bff' }
  }
  // fallback: 高斯模拟 (向后兼容)
  ...
}, [bffView, strikesResp, levels])
```

### 7.5 WebSocket 集成

```typescript
// hooks/useWebSocket.ts
export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)

  useEffect(() => {
    ws.current = new WebSocket(`ws://${host}/ws`)
    ws.current.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      setLastMessage(msg)
      queryClient.invalidateQueries(['signals'])
      queryClient.invalidateQueries(['gexmetrix'])
    }
    return () => ws.current?.close()
  }, [])

  return lastMessage
}
```

### 7.6 V3.0 玻璃拟态 UI

**设计令牌系统** — CSS 变量定义颜色/间距/圆角/阴影，`index.css` (475 行):

```css
/* index.css — V3.0 设计令牌 */
:root {
  --bg-primary: #0a0a1a;
  --bg-secondary: #111128;
  --glass-bg: rgba(255, 255, 255, 0.05);
  --glass-border: rgba(255, 255, 255, 0.1);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  --text-primary: #f0f0f5;
  --text-secondary: #a0a0b5;
  --accent-indigo: #6366f1;
  --accent-cyan: #22d3ee;
  --radius-lg: 16px;
  --spacing-md: 16px;
}
```

**双主题**: Dark/Light 通过 `themeStore` + CSS 变量一键切换。

**GlassCard 组件**:
```tsx
// components/GlassCard.tsx
export function GlassCard({ children, className, ...props }: GlassCardProps) {
  return (
    <div
      className={`glass-card ${className ?? ''}`}
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(12px)',
        border: '1px solid var(--glass-border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--glass-shadow)',
      }}
      {...props}
    >
      {children}
    </div>
  )
}
```

**数据陈旧度视觉**: `stale-warn` (泛黄) / `stale-card` (灰化) / `disconnected` (红框)

**动效系统**: 脉冲动画 (数据更新)、骨架屏 (加载中)、hover 抬起效果

### 7.7 V3.1 历史回放

**TimelineReplay 组件** — 时间滑块 + 播放/暂停控制 + 0.5x / 1x / 2x / 4x 倍速:

```tsx
// components/TimelineReplay.tsx
export function TimelineReplay({ snapshots, speed, onSeek, onPlay, onPause }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0)

  const handlePlay = useCallback(() => {
    onPlay()
    const interval = setInterval(() => {
      setCurrentIndex(prev => {
        if (prev >= snapshots.length - 1) {
          clearInterval(interval)
          onPause()
          return prev
        }
        onSeek(snapshots[prev + 1].timestamp)
        return prev + 1
      })
    }, 2000 / speed)
    return () => clearInterval(interval)
  }, [snapshots, speed, onSeek, onPlay, onPause])

  return (
    <GlassCard className="timeline-replay">
      <Slider value={currentIndex} max={snapshots.length - 1} onChange={setCurrentIndex} />
      <Button onClick={handlePlay}>▶ {speed}x</Button>
      <span>{snapshots[currentIndex]?.timestamp}</span>
    </GlassCard>
  )
}
```

**SnapshotGallery** — 按日期分组的快照画廊:
```tsx
// components/SnapshotGallery.tsx
export function SnapshotGallery({ snapshots, onSelect }: Props) {
  const grouped = useMemo(() => groupByDate(snapshots), [snapshots])

  return (
    <div className="snapshot-gallery">
      {Object.entries(grouped).map(([date, items]) => (
        <div key={date} className="gallery-day">
          <h3>{date}</h3>
          <div className="gallery-grid">
            {items.map(snap => (
              <GlassCard key={snap.timestamp} onClick={() => onSelect(snap.timestamp)}>
                <span>{snap.timestamp}</span>
                <span>Score: {snap.total_score?.toFixed(2)}</span>
              </GlassCard>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

**数据流切换**:
```typescript
// Dashboard.tsx — V3.1 回放模式
const { isReplayMode, currentTimestamp, playbackSpeed } = useReplayStore()

const scoresData = isReplayMode
  ? snapshotData   // 回放模式: 从快照加载
  : liveData       // 实时模式: 从 API 轮询

<TimelineReplay
  snapshots={snapshots}
  speed={playbackSpeed}     // 0.5x / 1x / 2x / 4x
  onSeek={(ts) => loadSnapshot(ts)}
  onPlay={() => setReplayMode(true)}
  onPause={() => setReplayMode(false)}
/>
```

### 7.8 Gamma 仪表盘 (V2.5 完整设计)

**4 维优化记录**:

#### 二.1 短期优化 — 模拟数据警示
```tsx
{strikesData.isReal ? (
  <span className="badge-green">✓ 真实数据 ({strikesData.strikes.length} strikes)</span>
) : (
  <span className="badge-yellow" title="...">⚠ 模拟数据</span>
)}
```

#### 二.2 数值格式化
```typescript
function formatGEX(value: number | null): string {
  if (value === null) return '-'
  const abs = Math.abs(value)
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`
  return value.toFixed(2)
}
```

#### 三.1 staleTime 拉满 5min
```typescript
useQuery({
  staleTime: 5 * 60 * 1000,
  refetchInterval: 5 * 60 * 1000,
})
```

#### 三.2 失败时刷新闭环
```typescript
const { data, isError, error, isFetching } = useGEXDashboardView(...)
return (
  <header>
    上次刷新: {lastUpdated.toLocaleTimeString()}
    {isError && <span className="text-red">⚠ 请求失败: {error.message}</span>}
    {isFetching && <Spinner />}
  </header>
)
```

#### A.1 历史数据源智能切换
```typescript
const HISTORY_LONG_THRESHOLD = 3

function useGEXHistory(symbol: string | null, days: number) {
  const effectiveDays = (symbol !== 'SPX' && days > HISTORY_LONG_THRESHOLD)
    ? HISTORY_LONG_THRESHOLD
    : days

  const [showBanner, setShowBanner] = useState(false)
  if (days !== effectiveDays) {
    setTimeout(() => setShowBanner(true), 0)
    setTimeout(() => setShowBanner(false), 5000)
  }

  const endpoint = effectiveDays > HISTORY_LONG_THRESHOLD
    ? `/gex/history?days=${effectiveDays}`
    : `/gex/${symbol}/history?days=${effectiveDays}`

  return useQuery({
    queryKey: ['gexmetrix', 'history', symbol, effectiveDays],
    queryFn: () => get(endpoint),
  })
}
```

**ECharts 主题配置**:
```typescript
export const resonanceV3Theme = {
  color: ['#6366f1', '#22d3ee', '#f59e0b', '#ef4444', '#10b981'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
  title: { textStyle: { color: 'var(--text-primary)' } },
  legend: { textStyle: { color: 'var(--text-secondary)' } },
  tooltip: {
    backgroundColor: 'var(--glass-bg)',
    borderColor: 'var(--glass-border)',
    extraCssText: 'backdrop-filter: blur(12px); border-radius: 12px;',
  },
}
```

**StrikeGexChart ECharts 配置**:
```typescript
const option = useMemo(() => ({
  tooltip: { trigger: 'axis', ...resonanceV3Theme.tooltip },
  legend: { data: ['Call GEX', 'Put GEX', 'Net GEX'] },
  xAxis: { type: 'category', data: strikes.map(s => s.strike) },
  yAxis: [
    { type: 'value', name: 'GEX ($)' },
    { type: 'value', name: 'OI' },
  ],
  series: [
    { name: 'Call GEX', type: 'bar', stack: 'gex',
      data: strikes.map(s => s.call_gex), itemStyle: { color: '#22d3ee' } },
    { name: 'Put GEX', type: 'bar', stack: 'gex',
      data: strikes.map(s => s.put_gex), itemStyle: { color: '#ef4444' } },
    { name: 'Net GEX', type: 'line', yAxisIndex: 0,
      data: strikes.map(s => s.net_gex), lineStyle: { width: 2 } },
  ],
}), [strikes])
```

### 7.9 性能指标 (V2.5)

| 指标 | v2.4 | v2.5 | 改善 |
|------|------|------|------|
| Gamma 首屏调用次数 | 6 个 useQuery (waterfall) | 1 个 BFF | -83% |
| 服务端响应时间 | 6 x ~1ms = 6ms | 7.3ms (含 200 strikes) | 单次取 6 倍数据 |
| 浏览器可见时间 | 6 x RTT | 1 x RTT | 显著下降 |
| 历史曲线完整度 | 3 天 (GEXMetrix) | 90 天 (SqueezeMetrics) | +30x |
| 行权价分布 | 高斯模拟 | 真实 OI x Gamma 加权 | 数据保真 |

---

## 8. 核心业务逻辑

### 8.1 共振评分细则

**四维加权求和** (满分 5.0):
```
total_score = gex_score + vix_score + crypto_score + darkpool_score
```

| 维度 | 满分 | 关键触发 |
|------|------|----------|
| GEX | 1.50 + 0.50 + 0.50 = 2.50 | Net GEX 转正 + Spot < Zero Gamma + 接近 Call Wall |
| VIX | 1.00 + 0.50 = 1.50 | 期限正挂 + 恐慌溢价低 |
| Crypto | 1.00 + 0.50 + 0.50 = 2.00 | 杠杆清洗 + 资金费率反转 + OI 暴跌 |
| Darkpool | 1.00 + 0.50 + 0.50 = 2.00 | DIX 看涨 + 做空极端 + EMA 动量反转 |

**LEVEL 划分**:
- LEVEL_1 (2.0-3.0): 观察，记入历史
- LEVEL_2 (3.0-3.5): 关注，前端红黄提示
- LEVEL_3 (>=3.5): 强信号，触发多渠道推送

### 8.2 Hawkes 自激分支比

**目的**: 量化信号的自激性(高自激 = 容易连环触发 = 抄底高置信)。

**模型**:
```
lambda(t) = mu + sum(alpha * lambda(t - t_i))   (Hawkes 自激过程)
lambda(t) = a + b*lambda(t-1)                    (AR(1) 简化)
```

**OLS 拟合** 求 `b` = branching ratio (0-1):
- b > 0.5: 高自激
- b in [0.2, 0.5]: 中等
- b < 0.2: 低自激

写入 `signal_alerts.hawkes_branching_ratio`，作为评分修正项。

### 8.3 历史回填 (90 天 SqueezeMetrics)

**脚本**: `scripts/backfill_gex_history.py`

**数据源**: SqueezeMetrics 公共 CSV (`https://squeezemetrics.com/monitor/dix`)

**流程**:
```python
1. 下载最新 DIX+ GEX CSV
2. 解析每日 (date, gex_local, gex_calibrated, put_wall_level, flip_zone_lower/upper)
3. 读 alpha_factor 从 system_config (默认 1.0)
4. 写入 gex_history (INSERT OR IGNORE 幂等)
5. 记录回填摘要: 起始日期、结束日期、新增行数
```

**调度**: 每周一美东 21:00 (`main_scheduler.py:task_backfill_gex_history`)

### 8.4 GEX 校准 (alpha_factor)

**问题**: GEXMetrix 与 SqueezeMetrics 量纲不同，需校准系数。

**存储**: `system_config.alpha_factor` (默认 1.0)

**校准方法**:
- 取 GEXMetrix `net_gex` 与 SqueezeMetrics `gex_calibrated` 历史比值
- 中位数作为 alpha
- EWM 平滑 (`alpha_history.ewm_alpha_20d`)

---

## 9. 快速开始

### 9.1 前置依赖

- Python 3.12+
- Node.js 18+
- SQLite (Python 内置)
- 操作系统: Linux / macOS / Windows

### 9.2 克隆 & 安装

```bash
# 1. 克隆仓库
git clone https://github.com/raymodny-ai/Multi-source-Resonance.git
cd Multi-source-Resonance

# 2. 安装 Python 依赖 (使用 uv 推荐)
uv venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
uv sync

# 或使用 pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量 (可选)
# 编辑 config/.env，填入 API Key:
#   GEXMETRIX_API_KEY (可选)
#   CCData_API_KEY (加密衍生品降级)
#   TELEGRAM_BOT_TOKEN / CHAT_ID
#   DISCORD_WEBHOOK_URL
#   OPENAI_API_KEY / ANTHROPIC_API_KEY (LLM 推理)

# 4. 初始化数据库 (首次运行自动创建)
python -c "from database.db_manager import DatabaseManager; DatabaseManager()"

# 5. 构建前端 (生产模式需要)
cd frontend
npm install
npm run build
cd ..
```

### 9.3 启动

```bash
# 方式 1: 完整服务 (推荐生产)
python api_server.py
# -> http://localhost:8524 (前端 + API + WebSocket)

# 方式 2: 仅后端 (开发)
uvicorn api_server:app --reload --host 0.0.0.0 --port 8524

# 方式 3: 调度器 (后台批量采集)
python main_scheduler.py

# 方式 4: 手动触发一次完整采集
curl -X POST http://localhost:8524/api/system/collect-manual
```

### 9.4 验证

```bash
# 健康检查
curl http://localhost:8524/api/health

# 数据源状态
curl http://localhost:8524/api/system/source-status

# GEX BFF
curl 'http://localhost:8524/api/gex/SPX/dashboard-view?strikes_limit=10'

# 回填 90 天历史
python scripts/backfill_gex_history.py --days 90
```

---

## 10. 部署

### 10.1 Docker

```bash
# 构建
docker build -t multi-source-resonance:latest .

# 运行 (生产模式，后端 + 前端 + Nginx)
docker-compose up -d

# 仅应用 (8524 端口)
docker run -d --name msr \
  -p 8524:8524 \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/data:/app/data \
  multi-source-resonance:latest

# 监控套件 (Prometheus + Grafana)
docker-compose --profile monitoring up -d
```

### 10.2 systemd 服务

```ini
# /etc/systemd/system/multi-source-resonance.service
[Unit]
Description=Multi-source Resonance API
After=network.target

[Service]
Type=simple
User=trim
WorkingDirectory=/opt/Multi-source-Resonance
ExecStart=/opt/Multi-source-Resonance/.venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now multi-source-resonance
sudo systemctl status multi-source-resonance
```

### 10.3 NAS 部署 (TRIM / Synology)

**当前部署**: TRIM NAS (Debian 12)，监听 `0.0.0.0:8524`
- 数据目录: `database/monitoring.db` (SQLite WAL)
- JSON 快照缓存: `data/gexmetrix/{symbol}/`
- 备份目录: `backups/`
- 日志: `logs/` (按日期轮转)

---

## 11. 测试

```bash
# 全量回归
pytest tests/ -v

# 信号引擎 (Layer1/2/3)
pytest tests/test_phase5_signal_engine.py -v

# 回测引擎
pytest tests/test_backtest_engine.py -v

# 集成测试
pytest tests/test_pipeline_integration.py -v

# 前端类型检查
cd frontend && npx tsc --noEmit

# 前端构建
cd frontend && npm run build

# 健康检查脚本
python check_status.py
```

---

## 12. 监控标的

### 12.1 GEX 域 (6 标的)

| Symbol | 描述 | 优先级 |
|--------|------|--------|
| **SPX** | S&P 500 指数期权 | 核心 |
| **SPY** | S&P 500 ETF | 核心 |
| **QQQ** | Nasdaq-100 ETF | 核心 |
| **IWM** | Russell 2000 ETF | 核心 |
| **NDX** | Nasdaq-100 指数期权 | 核心 |
| **VIX** | 波动率指数 | 核心 |

### 12.2 SqueezeMetrics 域 (SPX)

只有 SPX 有 SqueezeMetrics 90 天历史回填(其他标的需付费)。

---

## 13. 版本演进

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| **v1.0** | 2025-Q4 | 初版: FastAPI + WebSocket + 4 数据源 |
| **v2.0** | 2026-Q1 | **三层解耦架构** (Layer1/Layer2/Layer3 LLM) |
| **v2.1** | 2026-Q2 | 增加 Hawkes AR(1) 分支比 + 跨资产热力图 |
| **v2.2** | 2026-Q2 | 数据校验防线 (Pandera + Greeks 边界) |
| **v2.3** | 2026-05 | GEXMetrix 集成 + 7 数据源统一 |
| **v2.4** | 2026-05 | Web UI 重构 (React + TanStack Query) |
| **v2.5** | 2026-06 | **三通道监控** + 流动性门控 + BFF 聚合 + 逐 strike 真实分布 + 90 天回填 |
| **v2.6** | 2026-06 | LLM 输入脱敏 (SPX→Asset_A) + 幻觉检测 |
| **v3.0** | 2026-06 | **玻璃拟态 UI 现代化**: ECharts 6 迁移 + 双主题 + 设计令牌 + GlassCard + LiveTape |
| **v3.1** | 2026-07 | **历史回放 (Time-Travel)**: 快照时间线 + TimelineReplay + SnapshotGallery + 自动快照记录 |

**v2.5 详细变更**:

#### A — 智能切换历史数据源
- `useGEXHistory` 按 `days` 路由分流 (<=3 -> GEXMetrix, >3 -> SqueezeMetrics)
- 非 SPX + >3 天 -> 自动归位 3 天 + 5s 横幅提示
- `HISTORY_LONG_THRESHOLD = 3`

#### B — 真实逐 strike GEX/OI 分布
**关键发现**: GEXMetrix API 已有完整 `options[]` 数组(SPX 22650 合约)，只是 fetcher 没解析进 DB。

- `gexmetrix_fetcher.py:parse_strikes()` — OCC symbol 解析 + strike 聚合
- `gex_strikes` 新表 — 12 列，3300+ 行
- `extract_and_store_strikes()` helper — 给 scheduler 用
- `db_insert_gex()` 同时写 strikes
- 前端 `useGEXStrikes` hook + UI 切换 (水印 -> 真实)
- **bug 修复**: `save_snapshot` 函数体被破坏(filepath 返回 None)，导致实时采集 strikes 写入失效，已修复

#### C — BFF 聚合接口
- `GET /api/gex/{symbol}/dashboard-view` — 一次返回 6 个 section
- 替代前端 6 个独立 useQuery (消除 waterfall)
- `useGEXDashboardView` hook
- 响应时间 7.3ms (含 200 strikes)

**v3.0 详细变更**:

#### A — ECharts 6 迁移
- 从 Recharts 全面迁移到 ECharts 6.1 (echarts-for-react)
- 自定义 `resonance-v3` 主题，玻璃拟态 tooltip
- 新增 StrikeGexChart / MultiChannelChart / NetGexHistoryChart 组件

#### B — 设计令牌 + 双主题
- `index.css` (475 行) CSS 变量系统
- Dark/Light 主题通过 `themeStore` 一键切换
- GlassCard 组件: `backdrop-filter: blur()` + 半透明背景

#### C — LiveTape + 动效系统
- LiveTape 实时数据滚动纸带
- 脉冲动画 (数据更新)、骨架屏 (加载中)、hover 抬起效果
- 数据陈旧度视觉: `stale-warn` / `stale-card` / `disconnected`

**v3.1 详细变更**:

#### A — 快照自动记录
- `data/snapshot_recorder.py` — 每次 `/api/dashboard/scores` 自动记录 (5 分钟节流)
- 快照存储: `data/snapshots/` JSON 文件
- 后端 API: `/api/snapshots` / `/api/snapshots/stats` / `/api/snapshots/{timestamp}` / `/api/snapshots/capture`

#### B — TimelineReplay 回放控制
- 时间滑块 + 播放/暂停 + 0.5x / 1x / 2x / 4x 倍速
- `replayMode` 状态切换，快照数据与实时数据共享 DashboardScores 结构
- Dashboard.tsx 内嵌回放控制栏

#### C — SnapshotGallery 快照画廊
- 按日期分组的快照卡片网格
- 点击快照卡片直接 Time-Travel 到该时刻
- 显示时间戳 + 共振评分

---

## 14. 许可证

本项目为个人研究项目，所有数据版权归原始数据提供商所有。

数据源致谢:
- [GEXMetrix](https://www.gexmetrix.com) — 做市商 Gamma 敞口
- [SqueezeMetrics](https://squeezemetrics.com) — DIX / GEX 历史
- [FINRA](https://www.finra.org) — 做空数据
- [CBOE](https://www.cboe.com) — VIX 期限结构
- [Hyperliquid](https://hyperliquid.xyz) — 加密衍生品
- [yfinance](https://pypi.org/project/yfinance/) — OHLCV
- [AXLFI](https://www.axlfi.com) — 暗盘净头寸
- [DBMF](https://dbmf.co) — DBMF 均线

---

## 附录 A: 故障排查

### A.1 GEXMetrix 采集失败
**症状**: `[ERROR] GEXMetrix 核心标的拉取无数据返回`
**根因**: `save_snapshot` 函数体被破坏(filepath 返回 None)
**修复**: 见 `data_fetchers/gexmetrix_fetcher.py:save_snapshot`

### A.2 strikes 表为空
**症状**: `SELECT COUNT(*) FROM gex_strikes` 返回 0
**修复**:
```bash
# 手动回填
python -c "
import sys, json
sys.path.insert(0, '.')
from data_fetchers.gexmetrix_fetcher import GEXMetrixFetcher
from database.db_manager import DatabaseManager
fetcher = GEXMetrixFetcher()
db = DatabaseManager()
db._create_gex_strikes_table()
for sym in ['SPX','SPY','QQQ','IWM','NDX','VIX']:
    import os
    files = sorted(os.listdir(f'data/gexmetrix/{sym.lower()}'), reverse=True)
    if files:
        with open(f'data/gexmetrix/{sym.lower()}/{files[0]}') as f:
            data = json.load(f)
        n = fetcher.extract_and_store_strikes(sym, data, db)
        print(f'{sym}: {n} strikes')
"
```

### A.3 API 服务无响应
**症状**: `curl http://localhost:8524/api/health` 连接拒绝
**修复**:
```bash
# 查进程
ps -ef | grep api_server | grep -v grep
# 重启
pkill -f api_server.py
nohup python -u api_server.py > api_server.log 2>&1 &
```

---

## 附录 B: 性能调优

| 调优点 | 方法 | 预期效果 |
|--------|------|----------|
| 前端首屏 | 启用 BFF `dashboard-view` | 减少 6xRTT -> 1xRTT |
| GEX 采集 | 增加 ThreadPoolExecutor 大小 | 采集耗时 10s -> 6s |
| 历史回填 | 增大 `--days` 但限制 csv 下载 | 90 天回填 5s -> 3s |
| 数据库 | WAL + PRAGMA journal_size_limit | 并发写性能 +50% |
| LLM 推理 | 启用缓存 (Layer3 JSON hash) | 重复报告 2s -> 50ms |
| 快照记录 | 5 分钟节流避免磁盘 IO 过载 | 快照写入 <1ms |

---

<p align="center">
  <strong>Multi-source Resonance v3.1</strong><br>
  流动性真空→Gamma 挤压 Regime Transition 检测系统
</p>