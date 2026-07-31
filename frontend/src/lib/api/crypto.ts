/**
 * Crypto Derivatives API
 * 与 backend/api/routes/crypto.py 对齐
 * PRD §4.4 — funding rate, OI, liquidation, leverage ratio
 *
 * 字段以 crypto_derivatives 表为准（注意是 btc_funding_rate / btc_oi，不是 funding_rate / open_interest）
 */
import { get } from './client';
import type { CryptoRow } from './types';

export interface CryptoLatest extends CryptoRow {}

export interface CryptoHistoryRow {
  timestamp: string;
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

export async function getCryptoLatest(): Promise<CryptoLatest | null> {
  const r = await get<CryptoLatest | { message: string }>('/api/crypto/latest');
  if (r && typeof r === 'object' && 'message' in r) return null;
  return r as CryptoLatest;
}

export function getCryptoHistory(days = 30): Promise<CryptoHistoryRow[]> {
  return get<CryptoHistoryRow[]>('/api/crypto/history', { params: { days } });
}
