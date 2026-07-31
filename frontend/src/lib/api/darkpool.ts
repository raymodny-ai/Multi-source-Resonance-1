/**
 * Dark Pool API
 * PRD §4.5 — DIX, short ratio, EMA crossover, divergence signals
 */
import { get } from './client';

export interface DarkpoolLatest {
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
}

export interface DarkpoolHistoryRow {
  date: string;
  dix_value: number | null;
  v_net: number | null;
  ema_fast_5: number | null;
  ema_slow_20: number | null;
  aggregated_signal: boolean;
}

export function getDarkpoolLatest(): Promise<DarkpoolLatest> {
  return get<DarkpoolLatest>('/api/darkpool/latest');
}

export function getDarkpoolFlow(days = 30): Promise<DarkpoolHistoryRow[]> {
  return get<DarkpoolHistoryRow[]>('/api/darkpool/flow', { params: { days } });
}