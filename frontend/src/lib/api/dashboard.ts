/**
 * Dashboard API
 * 与 backend/api/routes/dashboard.py 对齐：返回嵌套结构（flattened-by-util）
 */
import { get } from './client';

export interface DashboardDataNormalized {
  /** 拉取时间戳 */
  fetched_at: string | null;
  /** 综合共振分数 0..5.0（来自 signal.total_score） */
  resonance_score: number | null;
  /** 当前警报等级 0..3（来自 signal.alert_level 字符串转换） */
  alert_level: number | null;
  alert_level_raw: string | null;
  /** 4 个维度分项（从 gex/vix/crypto/darkpool 提取） */
  gex_score: number | null;
  vix_score: number | null;
  crypto_score: number | null;
  darkpool_score: number | null;
  /** Hawkes 模型分枝比 */
  hawkes_branching_ratio: number | null;
  /** 最近一次 pipeline 完成时间 */
  last_cycle_at: string | null;
  /** mock 数据来源列表 */
  mock_sources: string[];
  /** 维度模拟标记 */
  is_mock_dims: Record<'gex' | 'vix' | 'crypto' | 'darkpool', boolean>;
}

export interface DataQualityResponse {
  total_sources: number;
  healthy_sources: number;
  quality_pct: number;
  sources: {
    source: string;
    age_minutes: number | null;
    last_data_ts: string | null;
    is_mock?: boolean;
    mock_reason?: string | null;
  }[];
  mock_sources: string[];
}

export interface RawDashboardResponse {
  fetched_at: string | null;
  gex: Record<string, unknown> | null;
  vix: Record<string, unknown> | null;
  crypto: Record<string, unknown> | null;
  darkpool: Record<string, unknown> | null;
  signal: Record<string, unknown> | null;
  _meta: { mock_sources: string[] };
}

/**
 * 拉取 Dashboard 原始响应
 */
export function getDashboardRaw(): Promise<RawDashboardResponse> {
  return get<RawDashboardResponse>('/api/dashboard');
}

function toNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** 信号 alert_level 字符串 → 数字 0..3 */
function alertLevelToNum(level: unknown): number | null {
  if (level === null || level === undefined) return null;
  if (typeof level === 'number') return level;
  const s = String(level).toUpperCase();
  if (s === 'LEVEL_1' || s === '1') return 1;
  if (s === 'LEVEL_2' || s === '2') return 2;
  if (s === 'LEVEL_3' || s === '3') return 3;
  if (s === 'NONE') return 0;
  return null;
}

/**
 * 把 Dashboard BFF 嵌套响应归一化为 DashboardDataNormalized
 * - signal 字段是 signal_alerts row
 * - gex/vix/crypto/darkpool 是各自表最新 row
 */
export function normalizeDashboard(raw: RawDashboardResponse): DashboardDataNormalized {
  const sig = (raw.signal ?? null) as Record<string, unknown> | null;
  const gex = (raw.gex ?? null) as Record<string, unknown> | null;
  const vix = (raw.vix ?? null) as Record<string, unknown> | null;
  const crypto = (raw.crypto ?? null) as Record<string, unknown> | null;
  const dp = (raw.darkpool ?? null) as Record<string, unknown> | null;

  const isMockOf = (payload: Record<string, unknown> | null): boolean => {
    const m = (payload?._meta ?? null) as Record<string, unknown> | null;
    return Boolean(m?.is_mock);
  };

  return {
    fetched_at: raw.fetched_at ?? null,
    resonance_score: toNum(sig?.total_score),
    alert_level: alertLevelToNum(sig?.alert_level),
    alert_level_raw: sig?.alert_level != null ? String(sig.alert_level) : null,
    gex_score: toNum(sig?.gex_score) ?? toNum(gex?.gex_score),
    vix_score: toNum(sig?.vix_score) ?? toNum(vix?.vix_score),
    crypto_score: toNum(sig?.crypto_score) ?? toNum(crypto?.crypto_score),
    darkpool_score: toNum(sig?.darkpool_score) ?? toNum(dp?.dix_value),
    hawkes_branching_ratio: toNum(sig?.hawkes_branching_ratio),
    last_cycle_at: toNum(sig?.trigger_time) != null
      ? String(sig?.trigger_time ?? '')
      : raw.fetched_at,
    mock_sources: raw._meta?.mock_sources ?? [],
    is_mock_dims: {
      gex: isMockOf(gex),
      vix: isMockOf(vix),
      crypto: isMockOf(crypto),
      darkpool: isMockOf(dp),
    },
  };
}

export function getDashboard(): Promise<DashboardDataNormalized> {
  return getDashboardRaw().then(normalizeDashboard);
}

export function getLatestSignal(): Promise<Record<string, unknown> | null> {
  return get('/api/signals/latest');
}

export function getDataQuality(): Promise<DataQualityResponse> {
  return get<DataQualityResponse>('/api/dashboard/data-quality');
}
