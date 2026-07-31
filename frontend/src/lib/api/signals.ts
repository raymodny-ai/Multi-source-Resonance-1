/**
 * Signals API
 */
import { get, post } from './client';
import type { PaginatedResponse, Signal, SignalLevelFilter, SignalOutcomeFilter } from './types';

export interface SignalHistoryParams {
  level?: SignalLevelFilter;
  outcome?: SignalOutcomeFilter;
  page?: number;
  limit?: number;
  search?: string;
  /** ISO date string YYYY-MM-DD */
  startDate?: string;
  /** ISO date string YYYY-MM-DD */
  endDate?: string;
}

export function getSignalsHistory(params: SignalHistoryParams = {}): Promise<PaginatedResponse<Signal>> {
  const search: Record<string, string | number> = {};
  if (params.level && params.level !== 'all') search.level = params.level;
  if (params.outcome && params.outcome !== 'all') search.outcome = params.outcome;
  if (params.search) search.search = params.search;
  if (params.startDate) search.start_date = params.startDate;
  if (params.endDate) search.end_date = params.endDate;
  search.page = params.page ?? 1;
  search.limit = params.limit ?? 25;
  return get<PaginatedResponse<Signal>>('/api/signals/history', { params: search });
}

export function getLatestSignal(): Promise<Signal | null> {
  return get<Signal | null>('/api/signals/latest');
}

export function acknowledgeSignal(id: number | string): Promise<{ id: number | string; acknowledged: boolean }> {
  return post(`/api/signals/${id}/acknowledge`);
}