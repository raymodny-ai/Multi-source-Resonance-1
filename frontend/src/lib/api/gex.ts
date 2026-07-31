/**
 * GEX (Gamma Exposure) API
 * 与 backend/api/routes/gex.py 对齐
 * PRD §4.2 — 主符号 SPX / SPY / QQQ / IWM / AAPL / MSFT
 *
 * 关键端点：
 * - GET /api/gex/{symbol}/dashboard-view — BFF 聚合（6 段，单次往返 <10ms）
 * - GET /api/gex/summary              — 全部符号最新汇总（list）
 * - GET /api/gex/history?days=90      — SqueezeMetrics 长历史
 * - GET /api/gex/alpha-history?days=90
 */
import { get } from './client';
import type {
  AlphaHistoryRow,
  GEXDashboardView,
  GEXHistoryRow,
  GEXSnapshotRow,
  GEXSummaryItem,
} from './types';

export type GEXSymbol = 'SPX' | 'SPY' | 'QQQ' | 'IWM' | 'AAPL' | 'MSFT';

/** BFF 聚合 — 单次返回 6 段 */
export function getGEXDashboardView(
  symbol: GEXSymbol,
  params: { historyDays?: number; longDays?: number; strikesLimit?: number } = {}
): Promise<GEXDashboardView> {
  const search: Record<string, number> = {};
  if (params.historyDays !== undefined) search.history_days = params.historyDays;
  if (params.longDays !== undefined) search.long_days = params.longDays;
  if (params.strikesLimit !== undefined) search.strikes_limit = params.strikesLimit;
  return get<GEXDashboardView>(`/api/gex/${symbol}/dashboard-view`, {
    params: Object.keys(search).length ? search : undefined,
  });
}

/** 全部符号 summary（list of latest snapshot per symbol） */
export function getGEXSummary(): Promise<GEXSummaryItem[]> {
  return get<GEXSummaryItem[]>('/api/gex/summary');
}

/** 全部符号长历史（GEX × SqueezeMetrics） */
export function getGEXHistory(days = 90): Promise<GEXHistoryRow[]> {
  return get<GEXHistoryRow[]>('/api/gex/history', { params: { days } });
}

/** Alpha factor 时间序列 */
export function getGEXAlphaHistory(days = 90): Promise<AlphaHistoryRow[]> {
  return get<AlphaHistoryRow[]>('/api/gex/alpha-history', { params: { days } });
}

/** 单符号最新 snapshot（兼容 PRD） */
export function getGEXLatest(symbol: GEXSymbol): Promise<GEXSnapshotRow | null> {
  return get<GEXSnapshotRow | null>(`/api/gex/${symbol}/latest`);
}

/** 单符号 strikes 数据 */
export function getGEXStrikes(symbol: GEXSymbol, limit = 200): Promise<{
  symbol: string;
  timestamp: string;
  spot_price: number | null;
  strike_count: number;
  strikes: GEXDashboardView['strikes'];
}> {
  return get(`/api/gex/${symbol}/strikes`, { params: { limit } });
}
