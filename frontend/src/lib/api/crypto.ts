/**
 * Crypto Derivatives API
 * PRD §4.4 — funding rate, OI, liquidation, leverage ratio
 */
import { get } from './client';

export interface CryptoLatest {
  symbol: string;
  funding_rate: number | null;
  open_interest: number | null;
  oi_change_1h: number | null;
  leverage_ratio: number | null;
  liquidation_spike: boolean;
  funding_anomaly: boolean;
  oi_crash: boolean;
  leverage_cleanup: boolean;
  timestamp: string;
}

export interface CryptoHistoryRow {
  timestamp: string;
  funding_rate: number | null;
  open_interest: number | null;
  oi_change_1h: number | null;
  leverage_ratio: number | null;
}

export function getCryptoLatest(): Promise<CryptoLatest> {
  return get<CryptoLatest>('/api/crypto/latest');
}

export function getCryptoHistory(hours = 168): Promise<CryptoHistoryRow[]> {
  return get<CryptoHistoryRow[]>('/api/crypto/history', { params: { hours } });
}