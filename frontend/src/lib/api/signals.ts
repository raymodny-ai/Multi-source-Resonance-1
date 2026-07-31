/**
 * Signals API
 * 与 backend/api/routes/signals.py 对齐：
 * - GET /api/signals/history → { items, total, offset, limit }（不是 data/total/page/limit）
 * - 字段以 signal_alerts 表为准（trigger_time / total_score / alert_level 字符串 等）
 */
import { get, post } from './client';
import type { Signal, SignalLevelFilter, SignalOutcomeFilter, SignalHistoryBackend, PaginatedResponse } from './types';

export interface SignalHistoryParams {
  level?: SignalLevelFilter;
  outcome?: SignalOutcomeFilter;
  /** 1-based page，会换算为 offset */
  page?: number;
  limit?: number;
  search?: string;
  /** ISO date string YYYY-MM-DD */
  startDate?: string;
  /** ISO date string YYYY-MM-DD */
  endDate?: string;
}

/**
 * 后端 offset = (page-1) * limit
 * 这里适配为前端期望的 { data, total, page, limit }
 */
export async function getSignalsHistory(params: SignalHistoryParams = {}): Promise<PaginatedResponse<Signal>> {
  const page = params.page ?? 1;
  const limit = params.limit ?? 25;
  const offset = (page - 1) * limit;
  const search: Record<string, string | number> = { offset, limit };
  if (params.level && params.level !== 'all') search.level = params.level;
  if (params.outcome && params.outcome !== 'all') search.outcome = params.outcome;
  if (params.search) search.search = params.search;
  if (params.startDate) search.start_date = params.startDate;
  if (params.endDate) search.end_date = params.endDate;

  const resp = await get<SignalHistoryBackend>('/api/signals/history', { params: search });
  return {
    data: resp.items ?? [],
    total: resp.total ?? 0,
    page,
    limit,
  };
}

export function getLatestSignal(): Promise<Signal | null> {
  return get<Signal | null>('/api/signals/latest');
}

/**
 * 确认信号
 * 后端 POST /api/signals/{signal_id}/acknowledge  → { ok, message }
 */
export function acknowledgeSignal(id: number | string): Promise<{ ok: boolean; message: string }> {
  return post(`/api/signals/${id}/acknowledge`);
}
