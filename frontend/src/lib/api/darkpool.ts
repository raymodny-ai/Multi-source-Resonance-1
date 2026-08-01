/**
 * Dark Pool / DIX metrics API
 * 与 backend/api/routes/darkpool.py 对齐
 * PRD §4.5 — DIX, short ratio, divergence signals, EMA crossovers
 */
import { get } from './client';
import type { DarkpoolRow } from './types';

export interface DarkpoolLatest extends DarkpoolRow {}

export interface DarkpoolHistoryRow {
  date: string;
  dix_value: number | null;
  v_net: number | null;
  ema_fast_5: number | null;
  ema_slow_20: number | null;
  aggregated_signal: boolean;
  zero_cross_signal: string | null;
  momentum_reversal_signal: string | null;
  // FIX-29: backend ``/api/darkpool/flow`` now exposes this column from
  // ``v_daily_darkpool``. The frontend Short Ratio series consumes it
  // directly instead of synthesising values from ``aggregated_signal``.
  chartexchange_short_ratio: number | null;
  [key: string]: unknown;
}

export async function getDarkpoolLatest(): Promise<DarkpoolLatest | null> {
  const r = await get<DarkpoolLatest | { message: string }>('/api/darkpool/latest');
  if (r && typeof r === 'object' && 'message' in r) return null;
  return r as DarkpoolLatest;
}

export function getDarkpoolFlow(days = 30): Promise<DarkpoolHistoryRow[]> {
  return get<DarkpoolHistoryRow[]>('/api/darkpool/flow', { params: { days } });
}

export function getDarkpoolHistory(days = 90): Promise<DarkpoolRow[]> {
  return get<DarkpoolRow[]>('/api/darkpool/history', { params: { days } });
}

export function getDarkpoolHistoryIntraday(days = 90): Promise<{
  date: string;
  timestamp: string;
  dix_value: number | null;
  gex_value: number | null;
  spx_price: number | null;
  chartexchange_short_ratio: number | null;
  source: string;
}[]> {
  return get('/api/darkpool/history-intraday', { params: { days } });
}
