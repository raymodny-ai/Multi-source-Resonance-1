/**
 * 后端 API 共享类型定义（与 backend FastAPI 实际响应 schema 对齐）
 *
 * 设计原则：
 * - 所有可空字段用 `| null` 显式标注，与 Pydantic 模型对齐
 * - 时间戳统一 ISO 8601 字符串
 * - 数值类型不带单位语义（如 ratio vs pct）由使用方决定
 *
 * 参考 backend/api/routes/*.py 确认响应 schema：
 * - dashboard.py 的 GET /api/dashboard 返回嵌套对象（不是扁平的）
 * - gex.py 的 /api/gex/{symbol}/dashboard-view 返回 6 段 BFF 聚合
 * - signals.py 的 /api/signals/history 返回 { items, total, offset, limit }
 * - config.py 的 /api/config 返回 { configs: [...], count }
 */

// ─── Dashboard ──────────────────────────────────────────────────────────────

/** 维度单点视图（来自 signal_alerts 或聚合维度结果） */
export interface DimensionScore {
  score: number | null;
  weight: number;
  /** 维度名：gex / vix / crypto / darkpool */
  dimension: string;
  /** 该维度是否处于 mock 数据状态 */
  is_mock: boolean;
  /** 错误信息（如有） */
  error?: string | null;
}

/**
 * Dashboard 主响应（与 backend/api/routes/dashboard.py GET /api/dashboard 对齐）
 * shape: { fetched_at, gex, vix, crypto, darkpool, signal, _meta: { mock_sources } }
 */
export interface DashboardData {
  /** 拉取时间戳 */
  fetched_at: string | null;
  /** 各维度的最新 row（具体字段取决于 gex/vix/crypto/darkpool 视图） */
  gex: Record<string, unknown> | null;
  vix: Record<string, unknown> | null;
  crypto: Record<string, unknown> | null;
  darkpool: Record<string, unknown> | null;
  /** signal_alerts 最新 row */
  signal: Record<string, unknown> | null;
  /** 元信息 */
  _meta: {
    mock_sources: string[];
  };
}

// ─── Signals ────────────────────────────────────────────────────────────────

export interface SignalOutcome {
  /** 1=profit, 0=breakeven, -1=loss, null=pending */
  result: 1 | 0 | -1 | null;
  /** 后续收益（如 +0.012 = +1.2%） */
  forward_return: number | null;
  evaluated_at: string | null;
}

/**
 * Signal 字段以 signal_alerts 表为准：
 * id, trigger_time, total_score, gex_score, vix_score, crypto_score, darkpool_score,
 * alert_level, hawkes_branching_ratio, acknowledged, acknowledged_at, acknowledged_by,
 * details ...
 */
export interface Signal {
  id: number | string;
  trigger_time: string;
  total_score: number | null;
  gex_score: number | null;
  vix_score: number | null;
  crypto_score: number | null;
  darkpool_score: number | null;
  alert_level: string | null;
  hawkes_branching_ratio: number | null;
  /** 信号是否已被人工确认 */
  acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  outcome: SignalOutcome | null;
  /** 原始 details JSON */
  details: Record<string, unknown> | null;
  /** 兼容旧字段：signal API 直接 select * from signal_alerts，可能带更多字段 */
  timestamp?: string;
  resonance_score?: number | null;
}

/**
 * 后端分页返回：{ items, total, offset, limit }
 * 这里输出适配前端的 { data, total, page, limit }
 */
export interface SignalHistoryBackend {
  items: Signal[];
  total: number;
  offset: number;
  limit: number;
}

export type SignalLevelFilter = 'all' | '1' | '2' | '3' | 'NONE';
export type SignalOutcomeFilter = 'all' | 'profit' | 'breakeven' | 'loss' | 'pending';

// ─── System ─────────────────────────────────────────────────────────────────

/**
 * /api/system/source-status 返回结构（list）
 */
export interface SourceStatus {
  name: string;
  status: 'online' | 'degraded' | 'offline' | string;
  method: string;
  availability_pct: number;
  last_data_ts: string | null;
  total_rows: number;
  age_minutes: number;
  last_error: string | null;
  is_mock: boolean;
  mock_reason: string | null;
  retry_count: number;
}

/**
 * /api/system/status 返回结构（CPU/MEM/DB 等）
 */
export interface SystemStatusInfo {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  db_size_mb: number;
  active_connections: number;
  uptime_seconds: number;
  python_version: string;
  platform: string;
}

export interface CollectionSourceDetail {
  source: string;
  is_mock: boolean;
  mock_reason: string | null;
  retry_count: number;
  error: string | null;
  records_written: number;
  elapsed_sec: number;
  tier: number;
}

export interface CollectionReport {
  cycle_ts: string | null;
  cycle_number: number;
  success_count: number;
  error_count: number;
  mock_count: number;
  sources: CollectionSourceDetail[];
  write_results: Record<string, unknown>;
}

// ─── GEX ────────────────────────────────────────────────────────────────────

/**
 * GEX 单 strike row（来自 gex_strikes 表 + BFF）
 */
export interface GEXStrikeRow {
  strike: number;
  call_gex: number | null;
  put_gex: number | null;
  call_oi: number | null;
  put_oi: number | null;
  call_vol: number | null;
  put_vol: number | null;
  net_gex: number | null;
}

/**
 * GEX long history row（来自 gex_history 表）
 */
export interface GEXHistoryRow {
  timestamp: string;
  symbol?: string;
  gex_local?: number | null;
  gex_calibrated?: number | null;
  alpha_factor?: number | null;
  gex?: number | null;
}

/**
 * Alpha factor history row（来自 alpha_history 表）
 */
export interface AlphaHistoryRow {
  timestamp: string;
  alpha_factor: number | null;
}

/**
 * GEX 单符号汇总视图行（来自 v_latest_gex_snapshot）
 */
export interface GEXSnapshotRow {
  symbol: string;
  timestamp: string;
  spot_price: number | null;
  call_wall: number | null;
  put_wall: number | null;
  zero_gamma_level: number | null;
  net_gex: number | null;
  call_gex: number | null;
  put_gex: number | null;
  alpha_factor?: number | null;
  [key: string]: unknown;
}

/**
 * GEX Dashboard-View BFF 响应（与 backend/api/routes/gex.py 对齐）
 * shape: { symbol, fetched_at, latest, levels, history, long_history, strikes, symbols }
 */
export interface GEXDashboardView {
  symbol: string;
  fetched_at: string;
  latest: GEXSnapshotRow | null;
  levels: {
    call_wall: number | null;
    put_wall: number | null;
    zero_gamma_level: number | null;
    spot_price: number | null;
    net_gex: number | null;
    call_gex: number | null;
    put_gex: number | null;
  } | null;
  /** 短窗口历史（GEXMetrix 1-7 天） */
  history: GEXSnapshotRow[];
  /** 长窗口历史（SqueezeMetrics 90 天） */
  long_history: GEXHistoryRow[];
  strikes: {
    timestamp: string | null;
    spot_price: number | null;
    strike_count: number;
    strikes: GEXStrikeRow[];
  } | null;
  symbols: {
    symbol: string;
    latest_timestamp: string;
    snapshot_count: number;
    age_minutes: number;
  }[];
}

/**
 * GEX summary（/api/gex/summary 返回的 list）
 */
export interface GEXSummaryItem extends GEXSnapshotRow {}

// ─── VIX ────────────────────────────────────────────────────────────────────

/**
 * VIX 分析 row（来自 vix_analysis 表）
 */
export interface VIXRow {
  timestamp: string;
  vix_spot: number | null;
  vx1: number | null;
  vx2: number | null;
  term_structure_ratio: number | null;
  term_structure_state: 'contango' | 'backwardation' | 'flat' | null;
  panic_premium: number | null;
  [key: string]: unknown;
}

/**
 * /api/vix/term-structure 直接返回（无 points 数组）
 */
export interface VIXTermStructure extends Omit<VIXRow, 'id'> {}

/**
 * VIX 期限结构历史 row（来自 vix_term_structure 表）
 */
export interface VIXTermStructureHistoryRow {
  date: string;
  vix_spot: number | null;
  vx_3m_proxy: number | null;
  term_structure_ratio: number | null;
  term_structure_state: string | null;
  panic_premium: number | null;
  regime: string | null;
}

// ─── Crypto ─────────────────────────────────────────────────────────────────

/**
 * Crypto 衍生品 row（来自 crypto_derivatives 表，与 backend /api/crypto/latest 对齐）
 */
export interface CryptoRow {
  timestamp: string;
  symbol?: string;
  btc_funding_rate: number | null;
  btc_oi: number | null;
  oi_change_1h: number | null;
  liquidation_spike: boolean;
  funding_anomaly: boolean;
  oi_crash: boolean;
  leverage_cleanup: boolean;
  cryptoquant_elr: number | null;
  [key: string]: unknown;
}

// ─── Darkpool ───────────────────────────────────────────────────────────────

/**
 * Darkpool row（来自 dark_pool_metrics 表）
 */
export interface DarkpoolRow {
  date: string;
  dix_value: number | null;
  chartexchange_short_ratio: number | null;
  stockgrid_20d_slope: number | null;
  stockgrid_60d_slope: number | null;
  stockgrid_divergence: boolean;
  dbmf_ma5_recovery: boolean;
  aggregated_signal: boolean;
  v_net: number | null;
  ema_fast_5: number | null;
  ema_slow_20: number | null;
  zero_cross_signal: string | null;
  momentum_reversal_signal: string | null;
  [key: string]: unknown;
}

// ─── Analysis ───────────────────────────────────────────────────────────────

/**
 * LLM 增强分析 row（与 backend /api/analysis/* 各页面 + 历史记录推断）
 * 实际后端 /api/analysis/* 返回 { ... derived fields, analysis: {...} }
 * 这里假定分析结果带历史 id 用于缓存/历史展示
 */
export interface AnalysisRecord {
  id?: number | string;
  generated_at?: string;
  timestamp?: string;
  confidence?: number;
  model?: string;
  text: string;
  /** 多模型一致性（1.0 完全一致） */
  verification_score?: number | null;
  cached?: boolean;
  sources_cited?: string[];
  [key: string]: unknown;
}

// ─── Config ─────────────────────────────────────────────────────────────────

/**
 * /api/config 返回 { configs: ConfigItem[], count }
 * 这里既支持集中字段，也支持原始 KV
 */
export interface ConfigItem {
  key: string;
  value: string;
  description: string | null;
  updated_at: string | null;
}

export interface ConfigResponse {
  configs: ConfigItem[];
  count: number;
}

/**
 * /api/metrics/summary 返回
 */
export interface MetricsSummary {
  uptime_seconds: number;
  pipeline: {
    running: boolean;
    cycles: number;
    fetchers: number;
  };
  event_bus: Record<string, unknown>;
  database: {
    size_mb: number;
    table_counts: Record<string, number>;
  };
}

// ─── WebSocket 消息 ─────────────────────────────────────────────────────────

/**
 * 后端 WS 消息格式（参考 backend/api/websocket.py）：
 * { topic: "GEXMETRIX_SNAPSHOT" | "SIGNAL" | "PIPELINE_CYCLE_COMPLETE" | ..., payload, timestamp }
 * 前端按 topic 直接使用，类型辅助见 WSMessage 简化包装
 */
export type WSTopic =
  | 'GEXMETRIX_SNAPSHOT'
  | 'SIGNAL'
  | 'SIGNAL_GENERATED'
  | 'SIGNAL_ALERT'
  | 'INCIDENT'
  | 'CONFIG'
  | 'DATA_FETCH_COMPLETE'
  | 'DATA_FETCH_ERROR'
  | 'DATA_MOCK_FALLBACK'
  | 'SCORING_COMPLETE'
  | 'PIPELINE_CYCLE_COMPLETE'
  | 'SYSTEM_CONFIG_CHANGE'
  | 'SYSTEM_START'
  | 'SYSTEM_STOP'
  | 'system'
  | string;

/**
 * 后端 WS 原始 payload（前端的 ws Provider 透传）
 */
export interface WSMessage<T = unknown> {
  topic: WSTopic;
  payload: T;
  timestamp?: string;
}

/**
 * 前端内部归一化消息类型（按 PRD §6 抽取 type）
 */
export type WSMessageType =
  | 'SIGNAL_ALERT'
  | 'SCORING_COMPLETE'
  | 'DATA_FETCH_COMPLETE'
  | 'DATA_MOCK_FALLBACK'
  | 'PIPELINE_CYCLE_COMPLETE'
  | 'ANALYSIS_COMPLETE'
  | 'GEXMETRIX_SNAPSHOT'
  | 'DATA_FETCH_ERROR'
  | 'CONFIG'
  | 'pong';

/**
 * 通用分页响应
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// ─── API 错误 ────────────────────────────────────────────────────────────────

export interface ApiError {
  status: number;
  code: string;
  message: string;
  url: string;
  timestamp: string;
}
