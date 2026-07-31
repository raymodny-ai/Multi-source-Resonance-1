/**
 * VIX API
 * PRD §4.3 — VIX spot, VX1/VX2, term structure state, panic premium
 */
import { get } from './client';

export interface VIXLatest {
  timestamp: string;
  vix_spot: number | null;
  vx1: number | null;
  vx2: number | null;
  term_structure_ratio: number | null;
  term_structure_state: 'contango' | 'backwardation' | 'flat' | null;
  panic_premium: number | null;
}

export interface VIXTermStructure {
  points: { tenor: string; price: number }[];
}

export interface VIXHistoryRow {
  date: string;
  vix_spot: number | null;
  vx_3m_proxy: number | null;
  term_structure_ratio: number | null;
  panic_premium: number | null;
}

export function getVIXLatest(): Promise<VIXLatest> {
  return get<VIXLatest>('/api/vix/latest');
}

export function getVIXTermStructure(): Promise<VIXTermStructure> {
  return get<VIXTermStructure>('/api/vix/term-structure');
}

export function getVIXHistory(days = 30): Promise<VIXHistoryRow[]> {
  return get<VIXHistoryRow[]>('/api/vix/history', { params: { days } });
}

export function getVIXTermStructureHistory(days = 365): Promise<VIXHistoryRow[]> {
  return get<VIXHistoryRow[]>('/api/vix/term-structure-history', { params: { days } });
}