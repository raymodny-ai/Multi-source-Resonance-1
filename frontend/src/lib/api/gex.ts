/**
 * GEX (Gamma Exposure) API
 * PRD §4.2 — 6 tracked symbols (SPX/SPY/QQQ/IWM/AAPL/MSFT)
 */
import { get } from './client';

export type GEXSymbol = 'SPX' | 'SPY' | 'QQQ' | 'IWM' | 'AAPL' | 'MSFT';

export interface GEXDashboardView {
  symbol: GEXSymbol;
  call_wall: number | null;
  put_wall: number | null;
  zero_gamma: number | null;
  alpha_factor: number | null;
  total_gex: number | null;
  /** 50 strikes: strike + gex + oi */
  strikes: { strike: number; gex: number; oi: number }[];
  history_90d: { date: string; gex: number; alpha_factor: number }[];
}

export function getGEXDashboardView(symbol: GEXSymbol): Promise<GEXDashboardView> {
  return get<GEXDashboardView>(`/api/gex/${symbol}/dashboard-view`);
}

export function getGEXHistory(symbol: GEXSymbol, days = 90): Promise<{ date: string; gex: number }[]> {
  return get(`/api/gex/history`, { params: { symbol, days } });
}

export function getGEXAlphaHistory(symbol: GEXSymbol, days = 90): Promise<{ date: string; alpha_factor: number }[]> {
  return get(`/api/gex/alpha-history`, { params: { symbol, days } });
}