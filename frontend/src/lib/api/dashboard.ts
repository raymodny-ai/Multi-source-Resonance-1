/**
 * Dashboard API
 * 与 backend/api/routes/dashboard.py 对齐：返回嵌套结构（flattened-by-util）
 */
import { get } from './client';

export interface DashboardDataNormalized {
  /** 拉取时间戳 */
  fetched_at: string | null;
  /** 综合共振分数 0..100（来自 signal.total_score，scoring.normalized_score） */
  resonance_score: number | null;
  /** 当前警报等级 0..3（来自 signal.alert_level 字符串转换） */
  alert_level: number | null;
  alert_level_raw: string | null;
  /** 4 个维度分项（0-100 归一化，来自 signal 的 gex/vix/crypto/darkpool 字段） */
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
  /** mock 数据来源数量（FIX-01：DB 持久化的 mock_count） */
  mock_count: number;
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
  _meta: { mock_sources: string[]; mock_count: number };
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

  // FIX-01: read DB-persisted `is_mock` column. The backend's data_writer
  // now persists `_meta.is_mock` from the fetcher into the corresponding
  // dimension table, and the dashboard route exposes it directly. The
  // previous `_meta` lookup was structurally impossible (SQLite rows have
  // no nested `_meta` key) so the UI never knew which dimensions were mocked.
  const isMockOf = (payload: Record<string, unknown> | null): boolean => {
    if (!payload) return false;
    // Accept both bool and integer (SQLite booleans serialize as 0/1).
    const v = payload.is_mock;
    return v === true || v === 1 || v === '1';
  };

  return {
    fetched_at: raw.fetched_at ?? null,
    resonance_score: toNum(sig?.total_score),
    alert_level: alertLevelToNum(sig?.alert_level),
    alert_level_raw: sig?.alert_level != null ? String(sig.alert_level) : null,
    gex_score: toNum(sig?.gex_score) ?? toNum(gex?.gex_score),
    vix_score: toNum(sig?.vix_score) ?? toNum(vix?.vix_score),
    crypto_score: toNum(sig?.crypto_score) ?? toNum(crypto?.crypto_score),
    // FE-02: darkpool fallback used to be ``toNum(dp?.dix_value)`` which
    // silently maps a 0..1 short-interest ratio onto the 0..100 score
    // axis. Show "—" instead so the UI does not pretend we have a
    // normalized score when the analyzer never produced one.
    darkpool_score: toNum(sig?.darkpool_score),
    hawkes_branching_ratio: toNum(sig?.hawkes_branching_ratio),
    // FE-01: previous version used ``toNum(trigger_time) != null`` as a
    // presence check, but ``toNum`` on an ISO string returns ``NaN`` and
    // ``NaN != null`` is ``true`` — so the comparison always passed and
    // the null branch was unreachable for valid ISO strings. Use a
    // direct non-empty-string check instead.
    last_cycle_at: (() => {
      const t = sig?.trigger_time;
      if (t != null && String(t).trim().length > 0) {
        return String(t);
      }
      return raw.fetched_at ?? null;
    })(),
    mock_sources: raw._meta?.mock_sources ?? [],
    mock_count: (() => {
      const v = raw._meta?.mock_count;
      const n = typeof v === 'number' ? v : Number(v);
      return Number.isFinite(n) && n >= 0 ? n : 0;
    })(),
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
