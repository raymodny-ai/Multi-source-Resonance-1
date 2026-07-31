/**
 * 后端 API 共享类型定义（与 backend FastAPI 响应 schema 对齐）
 *
 * 设计原则：
 * - 所有可空字段用 `| null` 显式标注，与 Pydantic 模型对齐
 * - 时间戳统一 ISO 8601 字符串
 * - 数值类型不带单位语义（如 ratio vs pct）由使用方决定
 */

// ─── Resonance ──────────────────────────────────────────────────────────────

/** 单维度评分（每个维度 0..max_weight） */
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

/** Dashboard 主响应 */
export interface DashboardData {
  /** 综合共振分数 0..5.0 */
  resonance_score: number | null;
  /** 当前警报等级 0..3 */
  alert_level: number | null;
  /** 4 个维度分项 */
  dimensions: DimensionScore[];
  /** Hawkes 模型分枝比（>1 表示自激） */
  hawkes_branching_ratio: number | null;
  /** 最近一次 pipeline 完成时间 */
  last_cycle_at: string | null;
  /** mock 数据来源列表（来自 _meta.mock_sources） */
  mock_sources: string[];
  /** 字段时间戳 */
  fetched_at: string | null;
}

// ─── Signals ────────────────────────────────────────────────────────────────

export interface SignalOutcome {
  /** 1=profit, 0=breakeven, -1=loss, null=pending */
  result: 1 | 0 | -1 | null;
  /** 后续收益（如 +0.012 = +1.2%） */
  forward_return: number | null;
  evaluated_at: string | null;
}

export interface Signal {
  id: number | string;
  timestamp: string;
  resonance_score: number | null;
  alert_level: number | null;
  gex_score: number | null;
  vix_score: number | null;
  crypto_score: number | null;
  darkpool_score: number | null;
  /** 信号是否已被人工确认 */
  acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  outcome: SignalOutcome | null;
  /** 原始 details JSON */
  details: Record<string, unknown> | null;
}

export interface SignalHistoryResponse {
  data: Signal[];
  total: number;
  page: number;
  limit: number;
}

export type SignalLevelFilter = 'all' | '1' | '2' | '3';
export type SignalOutcomeFilter = 'all' | 'profit' | 'breakeven' | 'loss' | 'pending';

// ─── System ─────────────────────────────────────────────────────────────────

export interface SourceStatus {
  name: string;
  status: string;
  is_mock: boolean;
  mock_reason: string | null;
  retry_count: number;
  last_error: string | null;
  last_success_at: string | null;
  tier: number;
}

export interface SystemHealth {
  uptime_sec: number;
  version: string;
  pipeline_status: 'running' | 'stopped' | 'paused' | 'error';
  last_cycle_at: string | null;
  sources: SourceStatus[];
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
  started_at: string;
  finished_at: string;
  total_sources: number;
  success_count: number;
  error_count: number;
  mock_count: number;
  source_details: CollectionSourceDetail[];
}

// ─── WebSocket 消息 ─────────────────────────────────────────────────────────

export type WSMessageType =
  | 'SIGNAL_ALERT'
  | 'SCORING_COMPLETE'
  | 'DATA_FETCH_COMPLETE'
  | 'DATA_MOCK_FALLBACK'
  | 'PIPELINE_CYCLE_COMPLETE'
  | 'ANALYSIS_COMPLETE'
  | 'pong';

export interface WSMessage<T = unknown> {
  type: WSMessageType;
  level?: 'info' | 'warning' | 'danger';
  payload?: T;
  timestamp?: string;
}

// ─── 通用分页 ────────────────────────────────────────────────────────────────

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