# 多源共振监控系统 — Multi-source Resonance

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-149eca)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-6-646cff)](https://vitejs.dev)
[![Spark Design](https://img.shields.io/badge/Spark_Design-0.4-ff6f61)](https://www.npmjs.com/package/sparkdesign)
[![ECharts](https://img.shields.io/badge/ECharts-6-e43961)](https://echarts.apache.org)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57)](https://sqlite.org/wal.html)
[![Tests](https://img.shields.io/badge/tests-187%20passed-success)](#15-测试)
[![Status](https://img.shields.io/badge/v4.1-Latest-success)](#)

> 基于 **三层解耦架构 V2.0** 的多维度金融监控系统。实时追踪美股暗盘资金、做市商 Gamma 敞口、VIX 期限结构、加密杠杆清洗及跨资产共振，通过 **四维 Regime Transition 评分** 自动识别“流动性清算衰竭”级抄底信号，多渠道推送告警。
>
> **v4.1**：完成数据获取与计算全面修复（**P0+P1+P2+P3 共 51 项** FIX），统一评分尺度为 0–100、加固安全默认、收紧 CORS、补齐 Hawkes/贝叶斯集成、修复 EventBus 泄漏与 VACUUM 锁争用。Frontend 仍是 React 19 + TypeScript + Spark Design 的指挥中心体验，支持桌面/平板/移动端响应式布局、实时 WebSocket、渐进式信息披露与全键可达性。

---

## 📑 目录

1. [项目概述](#1-项目概述)
2. [v4.0 前端重写亮点](#2-v40-前端重写亮点)
3. [系统架构](#3-系统架构)
4. [数据源矩阵](#4-数据源矩阵)
5. [数据架构](#5-数据架构)
6. [API 接口文档](#6-api-接口文档)
7. [后端设计](#7-后端设计)
8. [前端设计](#8-前端设计)
9. [核心业务逻辑](#9-核心业务逻辑)
10. [实时数据策略](#10-实时数据策略)
11. [设计令牌](#11-设计令牌)
12. [无障碍与响应式](#12-无障碍与响应式)
13. [快速开始](#13-快速开始)
14. [部署](#14-部署)
15. [测试](#15-测试)
16. [版本演进](#16-版本演进)
17. [许可证](#17-许可证)
18. [运维与安全配置（v4.1 必读）](#18-运维与安全配置v41-必读)

---

## 1. 项目概述

### 1.1 业务目标

**核心命题**：在美股市场识别 **"流动性清算衰竭"（Liquidity Cascade Exhaustion）** 级抄底信号 —— 即做市商对冲完毕、跨资产杠杆出清、Regime 从 Negative Gamma 翻转为 Positive Gamma 之后的低点。

**解决方案**：不是单一指标，而是 **多源共振** —— 当 **GEX 转正**（做市商从空 Gamma 反转为多 Gamma） + **VIX 期限倒挂缓解** + **加密杠杆清洗** + **暗池 DIX 底背离** 四维同时触发时，信号置信度最高。

### 1.2 核心能力

| 能力 | 描述 |
|------|------|
| **21 个数据源** | GEXMetrix / AXLFI / VIX / yfinance / CBOE / Crypto / Darkpool / Flow / Sentiment / LLM / Put-Call / VIX Term / Sector / Macro / SqueezeMetrics / FINRA / CCData / StockGrid / Coinglass / Tradier / DBMF，全部支持 mock 模式 |
| **三层解耦 V2.0** | Layer1 纯数学计算 → Layer2 JSON 网关 → Layer3 LLM 推理（任意一层可独立替换/降级） |
| **四维共振评分** | GEX + VIX + Crypto + Darkpool，满分 100（统一规范化的 0–100 尺度），LEVEL_1=25 / LEVEL_2=50 / LEVEL_3=75 |
| **Hawkes AR(1)** | OLS 自回归替代 corrcoef，精确自激分支比测算 |
| **贝叶斯权重自适应** | Beta-Binomial 共轭更新，动态调整四维权重 |
| **逐 strike 真实数据** | GEXMetrix options[] 解析，1666+ strikes 入库，前端真实可视化 |
| **90 天历史回填** | SqueezeMetrics CSV 回填到 `gex_history`，曲线完整时间序列 |
| **BFF 聚合接口** | `/api/gex/{symbol}/dashboard-view` 一次返回 6 个 section |
| **WebSocket 实时流** | `/ws` 长连接推送信号、告警、状态变更 |
| **降级容错** | Hyperliquid → CCData、yfinance → FINRA 双向降级 |
| **数据校验防线** | Pandera + Greeks 边界 + Put-Call Parity + 套利 + Isolation Forest |
| **BS 向量化引擎** | py-vollib-vectorized 批量 Greeks |
| **多渠道告警** | Email / Webhook / Telegram 并发推送 |
| **LLM 推理** | OpenAI / Anthropic / 模板 三级降级 + SHA-256 缓存 + 多 LLM 交叉验证 |
| **回测引擎** | 历史信号回放、Sharpe / MaxDD / WinRate、Walk-forward |
| **完整 Web UI（v4.0）** | React 19 + TypeScript + Spark Design UI + echarts-for-react + TanStack Query + Zustand |
| **指挥中心体验** | 9 页面、实时数据流、渐进式信息披露、响应式布局、无障碍访问 |

### 1.3 v4.1 当前状态（2026-07-31）

- **后端**：FastAPI 监听 `127.0.0.1:8524`（默认 SEC-09 收紧），63+ 个 REST 路由 + WebSocket（端口 `8524`，前端 Vite proxy 转发 `/api` & `/ws`）
- **数据库**：SQLite（WAL），11 张表，主要数据表：`gex_strikes` 3332 / `dark_pool_metrics` 253 / `gex_history` 103 / `gex_snapshots` 90+ / `vix_analysis` 7
- **前端**：React 19 + TypeScript 5.7，Vite 6 构建，Spark Design UI（`sparkdesign@^0.4.11`），echarts-for-react 图表
  - **9 页面**：Dashboard / Signals / GEX / VIX / Crypto / Darkpool / Analysis / System / Settings
  - **组件**：35+ 个（按页面分组，含 6 个 GEX、3 个 VIX、2 个 Crypto、2 个 Darkpool、3 个 Analysis、6 个 System、5 个 Settings、5 个 Dashboard、3 个 Signals、3 个公共）
  - **Hooks**：7 个 `use*`（Dashboard / Signals / GEX / VIX / Crypto / Darkpool / Analysis / System / Config）
  - **API 模块**：12 个 `lib/api/*`（client + 11 个领域模块）
- **采集**：21 个数据源 fetcher，全部支持 mock 模式（API key 缺失时自动降级）；每日美东 20:00 批量 + 手动触发（`POST /api/system/collect-manual`）
- **数据修复**：完成 **P0+P1+P2+P3 共 51 项 FIX**（详见 [§15 测试](#15-测试) 与 [§16 版本演进](#16-版本演进)）：mock 识别贯通、代理/网络配置、安全默认值收紧、CORS allowlist、连接池信号量 / 事务原子性、EventBus 排空 + 记录不可变、VACUUM 重试+延迟、UTC 列索引、Hawkes 分支比 / 贝叶斯权重全链路贯通、评分尺度统一 0–100、前端 UI 反馈闭环

---

## 2. v4.0 前端重写亮点

### 2.1 技术栈迁移

| 层 | v3.1 | v4.0 |
|----|------|------|
| 框架 | Vue 3 + `<script setup>` | React 19 + 函数组件 + Hooks |
| 语言 | TypeScript | TypeScript 5.7（类型放宽：`LineChart` 支持 `(number \| null)[]`） |
| UI 库 | 自研 GlassCard / Tailwind | Spark Design UI（`sparkdesign`）+ Tailwind 4 |
| 状态 | Pinia 4 个 store | Zustand（带 persist）+ TanStack Query |
| 图表 | ECharts + vue-echarts | ECharts + echarts-for-react |
| 路由 | Vue Router 4 | React Router v6 |
| 主题 | CSS 变量 + themeStore | Spark Design 双维度主题（theme + style） + CSS 变量 |

### 2.2 设计理念

- **指挥中心（Command Center）**：所有信息一屏可见，下钻时细节展开
- **渐进式信息披露**：Hero 指标 → 维度卡片 → 详情 Drawer / 表格
- **状态可视化**：loading skeleton / empty state / error retry / stale warning 完整闭环
- **响应式优先**：桌面 3 列 → 平板 2 列 → 移动单列 + 抽屉式侧栏
- **无障碍默认**：ARIA 全覆盖、`prefers-reduced-motion` 降级、键盘可导航

### 2.3 9 页面一览

| # | 路由 | 页面 | 关键组件 |
|---|------|------|----------|
| 1 | `/` | Dashboard 共振指挥中心 | ResonanceGauge + DimensionScoreCards + SignalTimeline + HawkesIntensity + SourceHealthGrid |
| 2 | `/signals` | 信号历史 & 管理 | SignalTable + FilterBar + SignalDetailDrawer + AcknowledgeDialog |
| 3 | `/gex` | Gamma 敞口分析 | GEXSymbolTabs + GEXKeyLevelsCard + GEXStrikesChart + GEXHistoryChart + GEXSymbolSummaryGrid |
| 4 | `/vix` | 波动率期限结构 | VIXMetricsCard + VIXTermStructureCard + VIXHistoryChart + PanicPremiumGauge |
| 5 | `/crypto` | 加密衍生品监控 | CryptoMetricsCard + CryptoHistoryChart + EventFlags |
| 6 | `/darkpool` | 暗池机构流动 | DarkpoolMetricsCard + DarkpoolHistoryChart + SignalFlags |
| 7 | `/analysis` | LLM 增强分析 | AnalysisLatestCard + AnalysisDimensionCard + HistoryList |
| 8 | `/system` | 系统健康 & 诊断 | SystemHeaderMetricsCard + SourceHealthTable + CollectionReportCard + SystemControlCard + MetricsCards + SystemLogsCard |
| 9 | `/settings` | 运行时配置 | SettingsOverviewCards + SettingsThemeCard + ConfigKVPanel + DataSourcesPanel + BayesianWeightsPanel |

### 2.4 实时数据策略

- **WebSocket 连接**：单条长连接 `/ws`，指数退避重连（1s → 2s → 4s → 8s → 15s 上限），30s 心跳
- **订阅**：连上后默认收所有 topic，前端按 view 过滤
- **缓存同步**：收到 `SIGNAL_ALERT` / `PIPELINE_CYCLE_COMPLETE` / `SCORING_COMPLETE` 等事件时 `queryClient.invalidateQueries` 对应 key
- **离线降级**：断连时显示"实时连接中断，展示缓存数据"横幅 + 重试按钮
- **陈旧度**：每张卡片显示"Last updated"，>5min 标注 stale

---

## 3. 系统架构

### 3.1 总体架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                Frontend (React 19 + Vite + Spark Design)               │
│   App Shell: Sidebar (nav + WS) + TopBar (title + alert + theme)      │
│   ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐     │
│   │Dashboard│ Signals │  GEX   │  VIX  │ Crypto │ DarkP  │Analysis│    │
│   │   /    │ /signals│ /gex  │ /vix  │/crypto │/darkp..│/analys.│    │
│   ├────────┴────────┴────────┴────────┴────────┴────────┴────────┤    │
│   │              System /settings + ErrorToast + WSProvider        │    │
│   │  TanStack Query (server state)  ·  Zustand (UI state)          │    │
│   │  Axios (HTTP, 拦截器 → msr-api-error 事件)                     │    │
│   │  WebSocket (auto-reconnect + heartbeat + topic filter)         │    │
│   └────────────────────┬──────────────────────┬────────────────────┘    │
│                        │ REST (63+ 路由)      │ WebSocket /ws             │
└────────────────────────┼──────────────────────┼──────────────────────────┘
                         ▼                      ▼
┌───────────────────────────────────────────────────────────────────────┐
│                  FastAPI Server (8525) — V2.0                         │
│   ┌───────────────────────────────────────────────────────────────┐   │
│   │                    REST API Layer (12 蓝图)                   │   │
│   │   /api/dashboard  /api/gex  /api/vix  /api/crypto  /api/darkp.│   │
│   │   /api/signals    /api/analysis  /api/system  /api/config     │   │
│   │   /api/metrics    /api/auth  /api/options_greeks  /ws        │   │
│   └───────────────────────────┬───────────────────────────────────┘   │
│                               │                                       │
│   ┌───────────────────────────▼───────────────────────────────────┐   │
│   │                  asyncio EventBus (pub/sub)                   │   │
│   │  Topics: SIGNAL_ALERT · SCORING_COMPLETE · PIPELINE_CYCLE_..  │   │
│   │  DATA_FETCH_COMPLETE · DATA_MOCK_FALLBACK · DATA_FETCH_ERROR  │   │
│   └───────────────────────────┬───────────────────────────────────┘   │
│                               │                                       │
│   ┌───────────────────────────▼───────────────────────────────────┐   │
│   │   Pipeline V2.0（fetchers → quant → scoring → 持久化 → WS）   │   │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │   │  Fetchers    │→ │ Quant        │→ │ Scoring      │         │
│   │   │  (21 个)     │  │ (13 分析器) │  │ (四维 0-5.0) │         │
│   │   └──────────────┘  └──────────────┘  └──────────────┘         │
│   └───────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────────────────┘
                            ▼
                  ┌──────────────────────┐
                  │  SQLite (WAL mode)   │
                  │  data/resonance.db   │
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │  Multi-channel       │
                  │  Email/Webhook/TG    │
                  └──────────────────────┘
```

### 3.2 三层解耦 V2.0

| Layer | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **Layer1 — 数学计算** | 纯 Python/numpy/pandas 计算 GEX、Z-Score、相关性、EMA、动量反转等 | 原始 OHLCV / OI / Greeks | 数值指标 + 触发布尔位 |
| **Layer2 — JSON 网关** | 序列化 Layer1 输出为标准化 JSON，作为契约边界；对接评分/告警 | Layer1 数值输出 | 评分结果 + 触发原因 + 上下文 |
| **Layer3 — LLM 推理** | 接收 Layer2 JSON，生成人类可读报告；API 失败可降级到模板 | Layer2 JSON + 历史 context | 自然语言报告 |

### 3.3 异步事件流（EventBus）

```
Data Fetcher → EventBus.publish(topic, payload)
                       │
                       ▼
            ┌──────────────────────┐
            │  asyncio.Queue       │
            │  (topic → queue 映射) │
            └──────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
   Signal          WebSocket       Notifier      Database
   Pipeline        Broadcast       Trigger       Writer
```

**核心 Topics**（WS 同时透传给前端）：

| Topic | 触发者 | 前端处理 |
|-------|--------|----------|
| `SIGNAL_ALERT` | Pipeline 检测到共振触发 | Dashboard gauge + Signals table 顶部插入 |
| `SCORING_COMPLETE` | 四维评分完成 | DimensionScoreCards 刷新 |
| `PIPELINE_CYCLE_COMPLETE` | 一轮采集 + 分析完成 | TopBar "Last updated" 时间戳 |
| `DATA_FETCH_COMPLETE` | 单源采集成功 | System 页面 source health |
| `DATA_MOCK_FALLBACK` | 采集降级到 mock | System warning toast |
| `DATA_FETCH_ERROR` | 采集失败 | ErrorToast 弹窗 |

### 3.4 目录结构

```
Multi-source-Resonance 1/
├── backend/                          # FastAPI 后端（Python 3.12）
│   ├── main.py                       # 应用入口（63+ 路由）
│   ├── config.py                     # 配置管理
│   ├── database.py                   # SQLite 异步 ORM
│   ├── api/
│   │   ├── middleware/               # auth (JWT) + rate_limit (slowapi)
│   │   ├── routes/                   # 12 个蓝图
│   │   └── websocket.py              # /ws 管理
│   ├── fetchers/                     # 21 个数据源 fetcher
│   ├── quant/                        # 13 个量化分析器 + scoring + 回测
│   ├── models/                       # Pydantic 数据契约
│   ├── eventbus/                     # asyncio pub/sub
│   ├── pipeline/                     # 数据流水线
│   ├── backtest_engine/              # 回测（walk-forward + sensitivity）
│   ├── llm_inference/                # LLM 推理
│   ├── notifications/                # 通知推送
│   ├── utils/                        # scheduler + security + maintenance + logging
│   └── tests/                        # unit + integration + conftest
├── frontend/                         # React 19 + Spark Design
│   ├── src/
│   │   ├── main.tsx                  # 应用入口
│   │   ├── App.tsx                   # 路由配置（9 页面）
│   │   ├── styles/
│   │   │   ├── tokens.css            # 设计令牌（颜色/间距/动画）
│   │   │   └── index.css             # 全局样式
│   │   ├── views/                    # 9 页面
│   │   │   ├── DashboardView.tsx
│   │   │   ├── GEXView.tsx
│   │   │   ├── VIXView.tsx
│   │   │   ├── CryptoView.tsx
│   │   │   ├── DarkpoolView.tsx
│   │   │   ├── SignalsView.tsx
│   │   │   ├── AnalysisView.tsx
│   │   │   ├── SystemView.tsx
│   │   │   └── SettingsView.tsx
│   │   ├── components/               # 35+ 组件
│   │   │   ├── AppLayout.tsx         # 响应式布局 + 移动端 drawer
│   │   │   ├── Sidebar.tsx           # 桌面/移动双变体
│   │   │   ├── TopBar.tsx            # 顶部导航 + 移动汉堡
│   │   │   ├── AlertBanner.tsx       # 通用提示（4 tone）
│   │   │   ├── ErrorToast.tsx        # 全局 API 错误堆叠
│   │   │   ├── EmptyState.tsx        # Empty / Error / Skeleton
│   │   │   ├── WSStatusIndicator.tsx # WebSocket 状态徽章
│   │   │   ├── dashboard/            # 5 个仪表盘子组件
│   │   │   ├── signals/              # 3 个信号子组件
│   │   │   ├── gex/                  # 6 个 GEX 子组件
│   │   │   ├── vix/                  # 3 个 VIX 子组件
│   │   │   ├── crypto/               # 2 个加密子组件
│   │   │   ├── darkpool/             # 2 个暗池子组件
│   │   │   ├── analysis/             # 2 个分析子组件
│   │   │   ├── system/               # 6 个系统子组件
│   │   │   └── settings/             # 5 个设置子组件
│   │   ├── lib/
│   │   │   ├── api/                  # 12 个 API 模块
│   │   │   ├── hooks/                # 9 个 TanStack Query hooks
│   │   │   ├── stores/               # Zustand stores
│   │   │   ├── ws/                   # WebSocket Provider + 心跳
│   │   │   └── utils/                # cn / format / signal 等
│   │   └── types/                    # 共享类型
│   ├── package.json
│   ├── vite.config.ts                # dev :5173 → proxy /api → :8524
│   └── tsconfig.json
├── data/                             # 运行时数据
│   ├── resonance.db / .db-shm / .db-wal
├── deploy/                           # 部署配置
│   ├── grafana_dashboard.json
│   └── prometheus_rules.yml
├── scripts/                          # cron / 回填脚本
├── docs/                             # 文档
├── requirements.txt
├── pyproject.toml
└── README.md                         # 本文档
```

---

## 4. 数据源矩阵

| 维度 | 数据源 | 频率 | 端点 | 关键字段 | 降级 |
|------|--------|------|------|----------|------|
| **GEX（做市商 Gamma）** | GEXMetrix | 盘中/批量 | `api.gexmetrix.com/api/files/{sym}/latest` | net_gex, call_wall, put_wall, zero_gamma, options[] | SqueezeMetrics |
| **GEX 历史回填** | SqueezeMetrics | 周一 21:00 | `squeezemetrics.com/dix` | gex_local, gex_calibrated, alpha_factor, flip_zone | — |
| **暗池 / DIX** | SqueezeMetrics | 日 | 同上 | dix_value, chartexchange_short_ratio, stockgrid_slope | FINRA short_interest |
| **暗盘净头寸** | AXLFI | 日 | AXLFI API | dark_net_position, dark_volume | — |
| **做空数据** | FINRA | 双周 | `api/data/groups/shortInterest` | short_interest, days_to_cover | yfinance |
| **价格 / OHLCV** | yfinance | 实时 | `query1.finance.yahoo.com` | open/high/low/close/volume | — |
| **VIX 期限结构** | CBOE | 日 | `cdn.cboe.com/api/us/...` | vix_spot, vx1, vx2, term_structure_ratio | — |
| **加密衍生品** | Hyperliquid | 实时 | `api.hyperliquid.xyz/info` | btc_funding, btc_oi, oi_change, liquidation_spike | CCData（需 Key） |
| **DBMF 均线** | DBMF ETF | 日 | DBMF API | dbmf_value, ma5, ma20, ma5_recovery | — |

---

## 5. 数据架构

### 5.1 数据库概览（11 张表）

```
┌─────────────────────────────────────────────────────────────────┐
│  GEX 域 (4 表)                                                  │
│  ├─ gex_snapshots         — GEXMetrix 摘要 (17 列, 90 行)       │
│  ├─ gex_strikes           — 逐 strike 真实 GEX/OI (12 列, 3332) │
│  ├─ gex_history           — SqueezeMetrics 日级历史 (8 列, 103)  │
│  └─ alpha_history         — alpha 因子历史 (9 列)               │
├─────────────────────────────────────────────────────────────────┤
│  其他维度域 (4 表)                                               │
│  ├─ vix_analysis          — VIX 期限结构 (9 列, 7 行)            │
│  ├─ dark_pool_metrics     — 暗池 DIX/EMA (18 列, 253 行)         │
│  ├─ crypto_derivatives    — 加密衍生品 (10 列, 26 行)            │
│  └─ system_config         — KV 配置 (3 行)                       │
├─────────────────────────────────────────────────────────────────┤
│  信号 & 审计域 (3 表)                                            │
│  ├─ signal_alerts         — 共振信号告警 (12 列)                │
│  ├─ validation_audit_log  — 数据校验日志 (14 列)                │
│  └─ gateway_snapshots     — Gateway 快照 (10 列)                │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 核心表 schema

#### `gex_snapshots` — GEXMetrix 摘要

```sql
CREATE TABLE gex_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,        -- SPX/SPY/QQQ/IWM/NDX/VIX
    timestamp       DATETIME NOT NULL,
    filename        TEXT NOT NULL,
    net_gex         REAL,                 -- 净 Gamma Exposure
    call_gex        REAL,                 -- Call 端 GEX 总和
    put_gex         REAL,                 -- Put 端 GEX 总和（负）
    zero_gamma_level REAL,                -- 零 Gamma 价位
    call_wall       REAL,                 -- Call Wall
    put_wall        REAL,                 -- Put Wall
    spot_price      REAL,
    total_gamma     REAL,
    file_size       INTEGER,
    created_at      DATETIME,
    quality_score   REAL,                 -- 0-1
    data_lag_seconds INTEGER,             -- 数据延迟（秒）
    oi_coverage_pct REAL                  -- OI 覆盖率 0-100
);
CREATE INDEX idx_gex_snapshots_sym_ts ON gex_snapshots (symbol, timestamp DESC);
```

#### `gex_strikes` — 逐 strike 真实分布

```sql
CREATE TABLE gex_strikes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    timestamp   DATETIME NOT NULL,
    strike      REAL NOT NULL,            -- 行权价
    call_gex    REAL NOT NULL DEFAULT 0,
    put_gex     REAL NOT NULL DEFAULT 0,
    call_oi     INTEGER NOT NULL DEFAULT 0,
    put_oi      INTEGER NOT NULL DEFAULT 0,
    call_vol    INTEGER NOT NULL DEFAULT 0,
    put_vol     INTEGER NOT NULL DEFAULT 0,
    net_gex     REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES gex_snapshots(id) ON DELETE CASCADE
);
CREATE INDEX idx_gex_strikes_sym_ts ON gex_strikes (symbol, timestamp DESC);
```

**GEX 聚合公式**（`gexmetrix_fetcher.py:parse_strikes`）：

```python
gex_value = gamma * oi * multiplier * spot * spot * 0.01
# SPY/QQQ/IWM: multiplier=100
# SPX 指数期权: multiplier=100
# 默认 min_oi=100 过滤深度虚值
```

#### `vix_analysis` — VIX 期限结构

```sql
CREATE TABLE vix_analysis (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    vix_spot              REAL,
    vx1                   REAL,
    vx2                   REAL,
    term_structure_ratio  REAL,            -- (vx2/vx1) - 1
    term_structure_state  TEXT,            -- 'contango' | 'backwardation' | 'flat'
    panic_premium         REAL,
    created_at            DATETIME
);
```

#### `dark_pool_metrics` — 暗池 / DIX

```sql
CREATE TABLE dark_pool_metrics (
    date                       DATE PRIMARY KEY,
    dix_value                  REAL,        -- Dark Index
    chartexchange_short_ratio  REAL,
    stockgrid_20d_slope        REAL,
    stockgrid_60d_slope        REAL,
    stockgrid_divergence       BOOLEAN,
    dbmf_ma5_recovery          BOOLEAN,
    dix_signal                 BOOLEAN,
    short_ratio_signal         BOOLEAN,
    stockgrid_signal           BOOLEAN,
    aggregated_signal          BOOLEAN,
    v_net                      REAL,
    ema_fast_5                 REAL,
    ema_slow_20                REAL,
    zero_cross_signal          TEXT,        -- 'bullish_cross' | 'bearish_cross'
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
    btc_oi             REAL,
    oi_change_1h       REAL,
    liquidation_spike  BOOLEAN,
    cryptoquant_elr    REAL,            -- Estimated Leverage Ratio
    funding_anomaly    BOOLEAN,
    oi_crash           BOOLEAN,
    leverage_cleanup   BOOLEAN,         -- 抄底关键信号
    created_at         DATETIME
);
```

#### `signal_alerts` — 共振信号告警

```sql
CREATE TABLE signal_alerts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_time            DATETIME NOT NULL,
    total_score             REAL NOT NULL,    -- 共振总分 0-100（FIX-38 规范化尺度）
    gex_score               REAL,             -- 0-100
    vix_score               REAL,             -- 0-100
    crypto_score            REAL,             -- 0-100
    darkpool_score          REAL,             -- 0-100
    alert_level             TEXT NOT NULL,    -- 'LEVEL_0' | 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3'
    hawkes_branching_ratio  REAL,
    details                 TEXT,             -- JSON 详情
    acknowledged            BOOLEAN,
    created_at              DATETIME
);
-- FIX-37: outcome/replay review扫描索引
CREATE INDEX idx_signal_alerts_outcome ON signal_alerts (outcome, outcome_checked_at DESC);
```

#### `system_config` — KV 配置

```sql
CREATE TABLE system_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  DATETIME
);
-- 默认值：
--   'alpha_factor'      = '1.0'        GEX 校准系数
--   'gex_threshold'     = '35000000'   GEX 阈值 35M
--   'alert_level_3_min' = '75.0'       LEVEL_3 最低分（0-100 尺度，FIX-38）
```

### 5.3 ER 图

```
gex_snapshots 1 ──< gex_strikes   (一对多：一次 snapshot 数百 strikes)
gex_snapshots 1 ──1 signal_alerts (一次 snapshot 可触发零或一信号)
dark_pool_metrics ──< signal_alerts (作为 darkpool_score 输入)
vix_analysis        ──< signal_alerts
crypto_derivatives  ──< signal_alerts
gex_history         ──< gex_snapshots  (作为回填基线)
system_config (KV)  ── 全局参数
```

---

## 6. API 接口文档

**Base URL**：`http://127.0.0.1:8524`（SEC-09：默认绑定 loopback；LAN 部署需设 `MSR_HOST=0.0.0.0`）
**CORS**：允许 `http://localhost:5173`、`http://localhost:3000`（FIX-10 收紧为 allowlist，不再 `*`）
**响应格式**：全部 `application/json`

### 6.1 健康 & 系统

| 方法 | 路径 | 说明 | 返回 |
|------|------|------|------|
| `GET` | `/api/health` | 健康检查 | `{status, timestamp, version, uptime_seconds}` |
| `GET` | `/api/status` | 系统状态（CPU/内存/连接数） | 系统指标 |
| `GET` | `/api/metrics` | Prometheus 风格指标 | 文本 |
| `GET` | `/api/system/source-status` | 23 数据源连通性 | `[{name, status, method, availability_pct, last_error}]` |
| `GET` | `/api/system/auto-polling` | 自动轮询状态 | `{enabled, schedule}` |
| `PUT` | `/api/system/auto-polling` | 切换自动轮询 | 同上 |
| `POST` | `/api/system/collect-manual` | 手动触发完整采集循环 | 8 数据源耗时统计 |

### 6.2 仪表盘聚合

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/dashboard/scores` | 当前四维共振评分 |
| `GET` | `/api/dashboard/recent-alerts` | 最近告警 |
| `GET` | `/api/dashboard/resonance-history` | 共振分数历史 |
| `GET` | `/api/dashboard/cross-asset-heatmap` | 跨资产热力图 |
| `GET` | `/api/dashboard/gex-curve?days=N` | GEX 长期曲线（SqueezeMetrics，默认 90 天） |
| `GET` | `/api/dashboard/multi-channel-curve` | 三通道（GEX + VEX + CHEX）曲线 |
| `GET` | `/api/dashboard/data-quality` | 流动性门控质量评分 |
| `GET` | `/api/dashboard/pipeline-metrics` | Pipeline 运行指标 |

### 6.3 GEX 元数据

| 方法 | 路径 | Query | 说明 |
|------|------|-------|------|
| `GET` | `/api/gex/symbols` | — | 所有可用标的 + 新鲜度 |
| `GET` | `/api/gex/summary` | — | 6 标的最新摘要 |
| `GET` | `/api/gex/history` | `days=N`（默认 90） | SqueezeMetrics 90 天历史 |
| `GET` | `/api/gex/{symbol}/latest` | — | GEXMetrix 最新快照 |
| `GET` | `/api/gex/{symbol}/history` | `days=N` | GEXMetrix 时间序列（≤7 天） |
| `GET` | `/api/gex/{symbol}/levels` | — | 关键价位（call_wall / put_wall / zero_gamma） |
| `GET` | `/api/gex/{symbol}/strikes` | `limit=N` | 逐 strike 真实分布（默认 200，最大 600） |
| `GET` | `/api/gex/{symbol}/dashboard-view` | `history_days=3&long_days=90&strikes_limit=200` | **BFF 聚合接口** |

**`/api/gex/{symbol}/dashboard-view` — BFF 聚合**：单次调用返回 6 个 section（latest / levels / history / long_history / strikes / symbols），消除前端 waterfall。

### 6.4 VIX / 暗池 / 加密

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/vix/latest` | VIX 即期 + 期限结构 |
| `GET` | `/api/vix/term-structure` | 期限结构曲线 |
| `GET` | `/api/vix/history?days=N` | VIX 历史 |
| `GET` | `/api/crypto/latest` | 加密衍生品当前指标 |
| `GET` | `/api/crypto/history?days=N` | 加密历史 |
| `GET` | `/api/darkpool/latest` | 暗池当前指标 |
| `GET` | `/api/darkpool/history?days=N` | 暗池历史 |

### 6.5 信号 & 告警 & 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/signals/latest` | 最近一次信号 |
| `GET` | `/api/signals/history` | 历史信号（分页 + level + outcome 过滤） |
| `POST` | `/api/signals/{id}/acknowledge` | 确认信号 |
| `GET` | `/api/analysis/latest` | 最近一次 LLM 分析 |
| `POST` | `/api/analysis/generate` | 触发新一轮 LLM 分析 |

### 6.6 配置 & 元数据

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/config` | 当前配置（含 keys + values + descriptions） |
| `PUT` | `/api/config` | 更新配置（写入 system_config + audit_log） |
| `POST` | `/api/config/restore` | 还原到默认 |
| `GET` | `/api/config/defaults` | 默认配置 |
| `GET` | `/api/config/audit` | 配置变更审计 |
| `GET` | `/api/tickers` | 可监控标的列表 |

### 6.7 WebSocket

```
WS /ws   （通过 Vite proxy → ws://localhost:8524/ws）
```

**消息格式**：

```json
{
  "topic": "SIGNAL_ALERT",
  "payload": { /* ... */ },
  "timestamp": "2026-07-31T05:49:51"
}
```

**核心 Topic 列表**：

- `SIGNAL_ALERT` — 共振信号触发
- `SCORING_COMPLETE` — 四维评分完成
- `PIPELINE_CYCLE_COMPLETE` — 一轮采集 + 分析完成
- `DATA_FETCH_COMPLETE` — 单源采集成功
- `DATA_MOCK_FALLBACK` — 采集降级到 mock
- `DATA_FETCH_ERROR` — 采集失败

---

## 7. 后端设计

### 7.1 FastAPI 启动流程

```python
# backend/main.py 启动序列

1. FastAPI app 创建
2. CORS 中间件（允许 :5173）
3. 数据库初始化（SQLite WAL, aiosqlite）
4. 加载配置（Settings）
5. EventBus()                  # asyncio 队列
6. 注册路由（12 个蓝图）
7. 注册中间件（JWT + Rate Limit）
8. start_scheduler()           # APScheduler
9. WebSocketManager()          # 管理 WS 连接 + 与 EventBus 桥接
10. uvicorn.run(host='127.0.0.1', port=8524)  # SEC-09 默认 loopback
```

### 7.2 异步并发模型

**采集并发**（`pipeline/concurrent_executor.py`）：

```python
async def collect_all_sources(self):
    tasks = [
        asyncio.create_task(self._poll_gexmetrix_once()),
        asyncio.create_task(self._poll_squeezemetrics_once()),
        asyncio.create_task(self._poll_vix_once()),
        asyncio.create_task(self._poll_darkpool_once()),
        asyncio.create_task(self._poll_crypto_once()),
        # ... 8 源并发
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 单源失败不影响整体
```

**线程池**：CPU 密集任务（`parse_strikes` 等）通过 `loop.run_in_executor` 提交到 `ThreadPoolExecutor`，避免阻塞 event loop。

### 7.3 信号流水线（V2.0）

```
GEXMetrix Snapshot
   │
   ▼
[Layer1: math]
   - 解析 options[] → 逐 strike 聚合
   - 计算 Call Wall / Put Wall / Zero Gamma
   - 计算 Net GEX / Total Gamma
   │
   ▼
[Layer2: gateway]
   - 序列化 Layer1 输出为标准 JSON
   - 注入上下文（timestamp, symbol, source）
   - 触发评分逻辑（gex_score / vix_score / ...）
   │
   ▼
[Score Aggregation]
   - total_score = Σ(dim_score × weight)
   - alert_level = level(total_score)
   - Hawkes AR(1) 分支比计算
   - Bayesian weights（Beta-Binomial 共轭更新）
   │
   ▼
[Layer3: LLM]
   - 接收 Layer2 JSON
   - 调 GPT-4o / Claude / 模板
   │
   ▼
[Notifier + DB Writer + WS Broadcast]
```

### 7.4 四维评分权重

```python
GEX_WEIGHTS = {
    "net_gex_positive": 1.50,           # GEX 转正（做市商反转）
    "zero_gamma_above_spot": 0.50,
    "call_wall_proximity": 0.50,
}
VIX_WEIGHTS = {
    "term_structure_contango": 1.00,    # 期限结构正挂（恐慌缓解）
    "panic_premium_low": 0.50,
}
CRYPTO_WEIGHTS = {
    "leverage_cleanup": 1.00,           # 杠杆清洗（抄底关键）
    "funding_anomaly": 0.50,
    "oi_crash": 0.50,
}
DARKPOOL_WEIGHTS = {
    "dix_bullish": 1.00,
    "short_ratio_extreme": 0.50,
    "momentum_reversal": 0.50,
}

LEVEL_THRESHOLDS = {
    "LEVEL_1": 25.0,   # 观察
    "LEVEL_2": 50.0,   # 关注
    "LEVEL_3": 75.0,   # 强信号 + 推送
}
# FIX-38: 统一规范化的 0–100 尺度，_basic_score / 贝叶斯权重动态适应均作用于同一标度。
```

### 7.5 降级容错

```python
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

**降级链**：

- Crypto：Hyperliquid → CCData（需 Key）→ 返回空 + 标记 OFFLINE
- Short Interest：FINRA → yfinance（估算）
- GEX：GEXMetrix → SqueezeMetrics（无逐 strike，只有日级）

### 7.6 数据校验防线

```python
class DataValidator:
    checks = [
        GreeksBoundsCheck(),       # gamma ∈ [-5, 5]
        PutCallParityCheck(),      # C - P ≈ S - K·exp(-rT)
        ArbitrageFreeCheck(),      # 无套利机会
        IsolationForestOutlier(),  # ML 异常检测
        PanderaSchemaCheck(),      # 列级 schema
    ]
```

校验日志写入 `validation_audit_log` 表，可追溯每条数据的校验失败原因。

---

## 8. 前端设计

### 8.1 技术栈

| 层 | 技术 | 版本 | 用途 |
|----|------|------|------|
| 构建 | Vite | 6 | 极速 HMR + 构建 |
| 框架 | React | 19 | 函数组件 + Hooks + Suspense |
| 语言 | TypeScript | 5.7 | 全量类型检查 |
| UI 库 | Spark Design | 0.4 | 设计系统（Card / Table / Drawer / Dialog / Select / Button / Switch / Alert 等） |
| CSS | Tailwind CSS | 4 | + CSS 变量设计令牌 |
| 状态 | Zustand | 5 | UI 状态（带 persist 中间件） |
| 服务端状态 | TanStack Query | 5 | 数据缓存 + 自动 refetch + 失效控制 |
| 图表 | echarts-for-react | 3 | 主题接入 tokens.css |
| HTTP | Axios | 1.7 | 拦截器 → `msr-api-error` 事件 |
| 路由 | React Router | 6 | 嵌套路由 + Layout 路由 |
| 工具 | clsx + tailwind-merge | — | className 合成 |

### 8.2 目录结构

```
frontend/src/
├── main.tsx                          # 应用入口（React + Router + QueryClient）
├── App.tsx                           # 路由配置（9 页面 + 错误边界）
├── styles/
│   ├── tokens.css                    # 设计令牌（颜色 / 间距 / 动画 / 关键帧）
│   └── index.css                     # 全局样式
├── views/                            # 9 个页面
│   ├── DashboardView.tsx
│   ├── GEXView.tsx
│   ├── VIXView.tsx
│   ├── CryptoView.tsx
│   ├── DarkpoolView.tsx
│   ├── SignalsView.tsx
│   ├── AnalysisView.tsx
│   ├── SystemView.tsx
│   └── SettingsView.tsx
├── components/
│   ├── AppLayout.tsx                 # 响应式布局 + 移动 drawer
│   ├── Sidebar.tsx                   # 桌面 / 移动双变体
│   ├── TopBar.tsx                    # 顶部导航 + 移动汉堡 + 主题切换
│   ├── AlertBanner.tsx               # 通用提示（4 tone + 自动消失）
│   ├── ErrorToast.tsx                # 全局 API 错误堆叠
│   ├── EmptyState.tsx                # Empty / Error / Skeleton 三态
│   ├── WSStatusIndicator.tsx         # WebSocket 状态徽章
│   ├── dashboard/                    # 仪表盘子组件（5）
│   ├── signals/                      # 信号子组件（3）
│   ├── gex/                          # GEX 子组件（6）
│   ├── vix/                          # VIX 子组件（3）
│   ├── crypto/                       # 加密子组件（2）
│   ├── darkpool/                     # 暗池子组件（2）
│   ├── analysis/                     # 分析子组件（2）
│   ├── system/                       # 系统子组件（6）
│   └── settings/                     # 设置子组件（5）
├── lib/
│   ├── api/                          # 12 个 API 模块
│   │   ├── client.ts                 # Axios + 拦截器 + msr-api-error
│   │   ├── types.ts                  # 共享响应类型
│   │   ├── dashboard.ts / signals.ts / gex.ts / vix.ts
│   │   ├── crypto.ts / darkpool.ts / analysis.ts
│   │   ├── system.ts / config.ts / metrics.ts
│   │   └── auth.ts
│   ├── hooks/                        # TanStack Query hooks（9）
│   │   ├── useDashboard.ts / useSignals.ts / useGEX.ts
│   │   ├── useVIX.ts / useCrypto.ts / useDarkpool.ts
│   │   ├── useAnalysis.ts / useSystem.ts / useConfig.ts
│   ├── stores/                       # Zustand stores
│   │   └── ui.ts                     # 主题 + WS 状态 + 侧栏状态
│   ├── ws/
│   │   └── WebSocketProvider.tsx     # 长连接 + 重连 + 心跳 + topic 路由
│   └── utils/                        # cn / format / signal 等
```

### 8.3 路由表

| 路径 | 页面 | 主要交互 |
|------|------|----------|
| `/` | Dashboard | 共振 Gauge + 维度卡片 + 信号时间线 + Hawkes + 数据源健康 |
| `/gex` | GEX | Symbol Tabs + Key Levels + Strikes Chart + History |
| `/vix` | VIX | Spot/VX1/VX2/Term + Curve + History + Panic Premium |
| `/crypto` | Crypto | Funding/OI/ELR + History + Event Flags |
| `/darkpool` | Darkpool | DIX/Short/Slope + History + Signal Flags |
| `/signals` | Signals | 过滤（level/outcome/date）+ 表格 + Drawer + Acknowledge |
| `/analysis` | Analysis | Request Analysis + Latest + History |
| `/system` | System | 4 指标 + 源健康表 + 采集报告 + 控制 + Metrics + Logs |
| `/settings` | Settings | 主题 + 配置 KV + 数据源 + 贝叶斯权重 + 总览 |

### 8.4 TanStack Query 模式

```typescript
// lib/hooks/useGEX.ts
export function useGEXDashboardView(
  symbol: GEXSymbol | null,
  options?: { history_days?: number; long_days?: number; strikes_limit?: number }
) {
  return useQuery<GEXDashboardView>({
    queryKey: ['gex', 'dashboard-view', symbol, options],
    queryFn: () => get<GEXDashboardView>(`/gex/${symbol}/dashboard-view`, options),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
    refetchInterval: symbol ? 5 * 60 * 1000 : false,
  });
}
```

**特性**：

- `staleTime: 5min` — 避免窗口聚焦时多余请求
- `refetchInterval: 5min` — 自动轮询
- `queryKey` 包含 params — 不同参数独立缓存
- `enabled: !!symbol` — 标的未选时不发请求

### 8.5 WebSocket 集成

```typescript
// lib/ws/WebSocketProvider.tsx
export function WebSocketProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const ws = new WebSocket(`ws://${host}/ws`);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      // 按 topic 路由到 Zustand + TanStack Query
      switch (msg.topic) {
        case 'SIGNAL_ALERT':
          qc.invalidateQueries({ queryKey: ['signals'] });
          useUIStore.getState().setLastSignal(msg.payload);
          break;
        case 'PIPELINE_CYCLE_COMPLETE':
          useUIStore.getState().setLastUpdate(msg.timestamp);
          break;
        // ...
      }
    };
    // 指数退避重连：1s → 2s → 4s → 8s → 15s
    return () => ws.close();
  }, []);
  return <>{children}</>;
}
```

### 8.6 设计与状态可视化

#### 设计令牌（`styles/tokens.css`）

```css
:root {
  /* 颜色 */
  --color-primary: #6366f1;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-info: #22d3ee;
  --color-text-primary: #f0f0f5;
  --color-text-secondary: #a0a0b5;
  --color-text-muted: #6b7280;

  /* 间距 */
  --space-1: 4px; --space-2: 8px; --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px;

  /* 圆角 */
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;

  /* 动画 */
  --transition-fast: 120ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 320ms cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes msr-fade-in { /* ... */ }
@keyframes msr-slide-in-up { /* ... */ }
@keyframes msr-slide-in-right { /* ... */ }
@keyframes msr-scale-in { /* ... */ }
@keyframes msr-pulse-dot { /* ... */ }
@keyframes msr-shimmer { /* ... */ }

.msr-skeleton { animation: msr-shimmer 1.6s linear infinite; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; }
}
```

#### 状态可视化闭环

```
加载 (isLoading)       →  msr-skeleton 骨架屏（shimmer 动画）
空 (data 空)           →  EmptyState（图标 + 标题 + 描述 + action）
错误 (isError)         →  AlertBanner tone="danger" + 重试按钮
陈旧 (dataStale)       →  卡片边框泛黄 + 提示"Last updated 6m ago"
实时 (WS connected)    →  顶部 WS 状态徽章 .animate-pulse-dot 绿色
```

---

## 9. 核心业务逻辑

### 9.1 共振评分细则

四维加权求和后归一化到 0–100（FIX-38）：

```
raw_score = (gex_score/100)*2.5 + (vix_score/100)*1.5 + (crypto_score/100)*2.0 + (darkpool_score/100)*2.0
normalized_score = (raw_score / 8.0) * 100
alert_level = level(normalized_score)        # LEVEL_0/1/2/3
```

| 维度 | 权重 | 原始范围 | 关键触发 |
|------|------|----------|----------|
| GEX | 2.5 | 0–100 | GEX 转正（+1.5）/ Spot < Zero Gamma（+0.5）/ 接近 Call Wall（+0.5） |
| VIX | 1.5 | 0–100 | 期限结构正挂（+1.0）/ Panic premium 低（+0.5） |
| Crypto | 2.0 | 0–100 | 杠杆清洗（+1.0）/ 资金费率异常（+0）/ OI 闪崩（+0） |
| Darkpool | 2.0 | 0–100 | DIX 多头（+1.0）/ 做空极端（+0.5）/ 动量反转（+0.5） |

**告警级别阈值**：`LEVEL_1 ≥ 25`，`LEVEL_2 ≥ 50`，`LEVEL_3 ≥ 75`。

> 多维共振奖励：当≥3个维度都处于"strong"区间（≥60）时，normalized_score 额外加上 5–10 分并重评告警级别。贝叶斯权重自适应该输出后利用 Beta-Binomial 共轭更新动态调整权重（`min_outcomes=1`，逐 outcome 递增）。

### 9.2 Hawkes 自激模型

将信号触发视为自激过程，OLS 拟合 `AR(1)` 模型：

```python
λ_t = μ + α Σ_{t_i < t} e^{-β(t-t_i)}
```

- 分支比 `n = α / β < 1` 表示过程平稳；`n ≥ 1` 表示级联触发。
- 替代了 `corrcoef` 相关性度量，提供更精确的"自激强度"指标。

### 9.3 贝叶斯权重自适应

四维权重 `w_i` 视为 Beta 分布先验，每次信号 outcome 反馈后共轭更新：

```python
w_i ~ Beta(α_i, β_i)
α_i += outcome_success_i
β_i += outcome_failure_i
```

通过 `beta_calibrator.py` 周期性刷新，使权重更贴合历史信号胜率。

---

## 10. 实时数据策略

| 关注点 | 实现方案 |
|--------|----------|
| 连接 | 单条 WebSocket → `/ws`，指数退避（1s → 2s → 4s → 8s → 15s 上限） |
| 心跳 | 每 30 秒发送 `{type: 'ping'}`，服务端 `pong` 回应 |
| 订阅 | 连上后默认收所有 topic，前端按 view 过滤 |
| 缓存同步 | `queryClient.invalidateQueries` 对应 key |
| 乐观更新 | Gauge 在 `SIGNAL_ALERT` 时 CSS 动画 `animate-scale-in` |
| 陈旧度 | 每张卡片显示 "Last updated"，>5min 显示 stale 标识 |
| 离线降级 | 断连时显示 `AlertBanner tone="warning"` + 重试按钮 |

---

## 11. 设计令牌

| 类别 | 令牌 | 用途 |
|------|------|------|
| 颜色 - 语义 | `--color-success / --color-warning / --color-danger / --color-info` | 状态标识、告警级别 |
| 颜色 - 图表 | 6 色分类调色板（GEX 靛蓝 / VIX 青 / Crypto 琥珀 / Darkpool 红 / 中性灰） | ECharts 系列 |
| 间距 | `--space-1` 至 `--space-8`（4px 基础栅格） | 卡片内边距 16/24px / 区块间距 24/32px |
| 圆角 | `--radius-sm: 4px` / `--radius-md: 8px` / `--radius-lg: 12px` | 按钮 / 卡片 |
| 字体 | Inter / system-ui（无衬线）；`font-mono`（数字） | 标题 / 数值 |
| 阴影 | `--shadow-sm` / `--shadow-md` / `--shadow-lg` | 卡片 / Drawer |
| 动画 | `--transition-fast: 120ms` / `--transition-base: 200ms` / `--transition-slow: 320ms` | 交互反馈 |

**主题**：Spark Design 双维度主题（theme: light/dark × style: 默认 / glassmorphism），CSS 变量一键切换。

---

## 12. 无障碍与响应式

### 12.1 响应式布局

| 断点 | 行为 |
|------|------|
| ≥ 1280px（桌面） | 完整 Sidebar + 2-3 列卡片网格 |
| 768 – 1279px（平板） | Sidebar 可折叠（图标模式）/ 2 列网格 / Drawer 全宽 |
| < 768px（移动） | Sidebar 隐藏 → 汉堡按钮 + 抽屉式 Drawer / 单列 / 图表堆叠 |

**优先级**：桌面优先，平板次之，移动可读但不优化交易交互。

### 12.2 无障碍

- 所有图表带 `aria-label` 摘要（数据范围 + 关键结论）
- 颜色编码同时使用图标与文字（不仅依赖颜色）
- 表格行 / Tabs / 过滤器支持键盘导航
- Spark Design 默认焦点环 + `*:focus-visible` 全局 2px 主色描边
- 告警级别通过文字标签传达，不仅依赖颜色
- `prefers-reduced-motion` 媒体查询自动关闭非必要动画
- "跳转到主内容" 隐藏链接（Tab 聚焦时显现）

---

## 13. 快速开始

### 13.1 后端

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（首次）
python -m backend.database init

# 3. 启动 FastAPI（默认 127.0.0.1:8524，SEC-09）
python -m backend.main
# 或
uvicorn backend.main:app --host 127.0.0.1 --port 8524 --reload
# LAN 部署需 --host 0.0.0.0；生产服务器需设 MSR_HOST=0.0.0.0
```

### 13.2 前端

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 开发模式（默认 :5173，proxy → :8524）
npm run dev

# 3. 生产构建
npm run build
npm run preview

# 4. 类型检查
npm run type-check
```

### 13.3 一次性启动（开发）

```bash
# 终端 1：后端
python -m backend.main

# 终端 2：前端
cd frontend && npm run dev
```

打开 <http://localhost:5173> 即可。

### 13.4 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `MSR_BACKEND_PORT` | 后端端口 | `8524` |
| `MSR_FRONTEND_PORT` | 前端端口 | `5173` |
| `MSR_DB_PATH` | SQLite 数据库路径 | `data/resonance.db` |
| `MSR_API_KEY_<SOURCE>` | 各数据源 API Key | — |
| `MSR_OPENAI_API_KEY` | LLM 推理 Key | — |

复制 `.env.example` → `.env` 并填写。

---

## 14. 部署

### 14.1 单机部署

```bash
# 后端 systemd / supervisor
python -m backend.main   # 或 gunicorn

# 前端 nginx 静态托管
cd frontend && npm run build
# dist/ → nginx /var/www/msr
```

Nginx 反向代理示例：

```nginx
server {
  listen 80;
  server_name msr.example.com;

  location / {
    root /var/www/msr;
    try_files $uri /index.html;
  }

  location /api/ {
    proxy_pass http://localhost:8524;
  }

  location /ws {
    proxy_pass http://localhost:8524;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
```

### 14.2 Docker

```bash
docker-compose up -d
```

### 14.3 监控

- Prometheus 规则：`deploy/prometheus_rules.yml`
- Grafana 仪表盘：`deploy/grafana_dashboard.json`

---

## 15. 测试

### 15.1 后端

```bash
cd backend
pytest tests/unit -v
pytest tests/integration -v
pytest tests/ -v --cov=backend
```

**当前状态（v4.1）**：

| 测试套件 | 用例数 | 状态 |
|----------|--------|------|
| `tests/unit/test_db_maintenance.py` | 8 | ✓ |
| `tests/unit/test_eventbus.py` | 22 | ✓ |
| `tests/unit/test_fetchers.py` | 24 | ✓ |
| `tests/unit/test_models.py` | 34 | ✓ |
| `tests/unit/test_quant.py` | 41 | ✓ |
| `tests/unit/test_security.py` | 19 | ✓ |
| `tests/integration/test_api.py` | 19 | ✓ |
| `tests/integration/test_pipeline.py` | 12 | ✓ |
| `tests/test_performance.py` | 7 | ✓ |
| **合计** | **187** | **全部通过** |

最近一次运行耗时约 27 秒（pytest 9 + Python 3.12）。

### 15.2 前端

```bash
cd frontend
npm run type-check      # tsc 严格类型检查（当前零错误）
npm run build           # Vite 生产构建
```

### 15.3 性能基线

| 指标 | 目标 |
|------|------|
| Dashboard 冷启动 | < 2s |
| Dashboard 热启动 | < 500ms |
| WS 断线重连 | < 5s 无需用户介入 |
| 9 页面在 1280px / 768px | 正确渲染 |
| Signal Acknowledge | ≤ 2 次点击 |
| TypeScript `any` 数量 | 0 |
| Lighthouse Accessibility | ≥ 90 |

---

## 16. 版本演进

| 版本 | 日期 | 关键变更 |
|------|------|----------|
| **v1.0** | 2025-Q3 | 初版：单 fetcher + 简单阈值告警 |
| **v2.0** | 2025-Q4 | 三层解耦架构 + EventBus + 多 fetcher 并发 |
| **v2.5** | 2026-Q1 | 逐 strike 真实数据 + BFF 聚合接口 + 90 天历史回填 |
| **v3.0** | 2026-Q2 | 玻璃拟态 UI + 设计令牌 + 双主题 + LiveTape |
| **v3.1** | 2026-Q3 | 快照自动记录 + TimelineReplay + SnapshotGallery |
| **v4.0** | 2026-Q4 | **前端重写：Vue 3 → React 19 + Spark Design UI**，9 页面 + 响应式 + 无障碍 + WebSocket 优化 |
| **v4.1** | 2026-07-31（当前） | **数据获取与计算全面修复（51 项 FIX）**：P0 安全默认 + P1 竞态/降级 + P2 事件流/UI + P3 代码质量。最终 187 个后端测试全部通过 + 前端 `tsc --noEmit` 零错误。 |

### v4.1 修复总览（51 项）

| 阶段 | 修复点 | 重点 |
|------|--------|------|
| **P0 阻塞部署** | FIX-01~10 | mock 检测贯通、代理/网络配置、评分阈值统一 0–100、维度/仪表盘尺度、移除硬编码 JWT/CORS allowlist、连接池信号量防泄露、事务原子性、状态端点加认证 |
| **P1 一周内** | FIX-11~22 | fetcher mock 标记、PutCallFetcher mock 标记、消除随机字段、Hawkes 集成、VIX/Crypto 历史 "最近" 标签、UI 错误反馈 |
| **P2 两周内** | PIPE-08/09/13/16、FE-01/02/05~15、SEC-03/05/10/11/13~18 | EventBus drain + 不可变记录、VACUUM retry+defer、scheduler is_writing、darkpool short_ratio + EMA axis、ErrorToast sweep 间隔、AlertBanner key、SignalTimeline 标签、VIX 期限比率、GEX WS 精准失效、Redis 限流、信任代理、主机默认 127.0.0.1、安全响应头中间件、Vite host 可选 |
| **P3 后续质量** | FIX-37~51 | signal_alerts outcome 索引、fmtPct 契约、mockSources 稳定引用、Bayesian DIMS 常量、aria-expanded、WS URL 端口、骨架高度、Darkpool 日期拼接、SourceHealthGrid 集中式 hook、GEX markPoint 类别轴、GEX null 一致性、WSProvider init ref |

---

## 17. 许可证

本项目仅供内部研究使用，未经授权不得用于商业用途。

---

## 18. 运维与安全配置（v4.1 必读）

### 18.1 环境变量要点

复制 `.env.example` → `.env`，并**必须**设置以下变量（避免使用默认值）：

| 变量 | 说明 | 缺省行为 |
|------|------|----------|
| `JWT_SECRET` | JWT 签名密钥（FIX-05） | 不设 → 生成**本次进程内临时密钥**，重启后所有 token 失效 |
| `MSR_HOST` | 后端绑定地址（SEC-09） | 默认 `127.0.0.1`；LAN 部署需设 `0.0.0.0` |
| `CORS_ORIGINS` | CORS allowlist（FIX-10） | 默认 `http://localhost:5173,http://localhost:3000`；`*` 会被启动拒绝 |
| `MSR_HTTP_PROXY` / `MSR_HTTPS_PROXY` | 代理地址（FIX-02） | 不设 → 直连 |
| `MSR_NETWORK_ENABLED` | 是否允许出站网络 | 默认 `true`；设 `false` → 全部数据源走 mock |
| `MSR_REDIS_URL` | 分布式限流后端（SEC-07） | 不设 → 本地内存限流 |
| `MSR_TRUST_PROXY` | 信任反向代理（SEC-08） | 默认 `false`；需准确 X-Forwarded-* 时设 `true` |

### 18.2 部署前检查清单

- [ ] 设置 `JWT_SECRET`（≥32 字节随机串）
- [ ] 根据实际部署场景设置 `MSR_HOST` 和 `CORS_ORIGINS`
- [ ] 如走代理，设置 `MSR_HTTPS_PROXY`（或 `proxy_overrides` JSON）
- [ ] 如跨域需分布式限流，部署 Redis 并设 `MSR_REDIS_URL`
- [ ] 反向代理后面设 `MSR_TRUST_PROXY=true`，并在 nginx 严格设置 `X-Forwarded-*`
- [ ] 若裸机部署且需 LAN 访问，设 `MSR_VITE_HOST=0.0.0.0`
- [ ] 首次启动后检查 `/api/health` 返回 200 与 `version`

### 18.3 VACUUM 维护

`vacuum_and_analyze` 现在走 **WAL checkpoint → 重试 + defer** 路径（FIX-25）。cron 周期中如遇到 `status=deferred`，说明被写入锁压住，会在下个周期重试，不会报“错误”误导运营。

---

> 详细 PRD 与设计规格请参见 [`PRD_Multi-Source-Resonance-UI-Redesign.md`](./PRD_Multi-Source-Resonance-UI-Redesign.md)。
> 数据获取优先级修复待办请参见 [`DATA_FETCH_FIX_TODO.md`](./DATA_FETCH_FIX_TODO.md)。