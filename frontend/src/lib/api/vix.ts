/**
 * VIX API
 * 与 backend/api/routes/vix.py 对齐
 * PRD §4.3 — VIX spot, VX1/VX2, term structure state, panic premium
 *
 * 端点：
 * - GET /api/vix/latest                  → vix_analysis 最新 row
 * - GET /api/vix/term-structure          → { vix_spot, vx1, vx2, ratio, state, panic_premium }
 * - GET /api/vix/history?days=30         → vix_analysis rows
 * - GET /api/vix/term-structure-history  → vix_term_structure 历史
 */
import { get } from './client';
import type { VIXRow, VIXTermStructure, VIXTermStructureHistoryRow } from './types';

export interface VIXLatest {
  timestamp: string;
  vix_spot: number | null;
  vx1: number | null;
  vx2: number | null;
  term_structure_ratio: number | null;
  term_structure_state: 'contango' | 'backwardation' | 'flat' | null;
  panic_premium: number | null;
  [key: string]: unknown;
}

/**
 * /api/vix/latest 可能返回：
 * - "message" 字段（无数据）
 * - vix_analysis 完整 row
 */
export async function getVIXLatest(): Promise<VIXLatest | null> {
  const r = await get<VIXLatest | { message: string } | VIXRow>('/api/vix/latest');
  if (r && typeof r === 'object' && 'message' in r) return null;
  return r as VIXLatest;
}

/** 期限结构（单点） */
export function getVIXTermStructure(): Promise<VIXTermStructure | null> {
  return get<VIXTermStructure | { message: string }>('/api/vix/term-structure').then((r) =>
    r && typeof r === 'object' && 'message' in r ? null : (r as VIXTermStructure)
  );
}

/** VIX 历史（vix_analysis 表） */
export function getVIXHistory(days = 90): Promise<VIXRow[]> {
  return get<VIXRow[]>('/api/vix/history', { params: { days } });
}

/** VIX 期限结构历史（vix_term_structure 表） */
export function getVIXTermStructureHistory(days = 365): Promise<VIXTermStructureHistoryRow[]> {
  return get<VIXTermStructureHistoryRow[]>('/api/vix/term-structure-history', { params: { days } });
}
