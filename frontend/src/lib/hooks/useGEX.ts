/**
 * TanStack Query hooks — GEX (Gamma Exposure)
 * 包含：
 * - useGEXSummary  所有符号最新汇总
 * - useGEXDashboardView  单符号 BFF
 * - useGEXLatest / useGEXStrikes  / useGEXHistory / useGEXAlphaHistory
 * - useGEXSymbolSelection  本地 Tabs 选中状态
 * - useGEXWSSync          监听 GEXMETRIX_SNAPSHOT 实时刷新
 */
import { useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getGEXSummary,
  getGEXDashboardView,
  getGEXLatest,
  getGEXStrikes,
  getGEXHistory,
  getGEXAlphaHistory,
} from '@/lib/api/gex';
import type { GEXSymbol } from '@/lib/api/gex';

export type { GEXSymbol };
import { useUIStore } from '@/lib/stores/ui';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

/** 6 个主符号（与 PRD §4.2 一致） */
export const GEX_SYMBOLS: GEXSymbol[] = ['SPX', 'SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT'];

export function useGEXSummary() {
  return useQuery({
    queryKey: ['gex', 'summary'],
    queryFn: getGEXSummary,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

export function useGEXDashboardView(
  symbol: GEXSymbol,
  options: { historyDays?: number; longDays?: number; strikesLimit?: number; enabled?: boolean } = {}
) {
  const { historyDays = 7, longDays = 90, strikesLimit = 60, enabled = true } = options;
  return useQuery({
    queryKey: ['gex', 'dashboard-view', symbol, historyDays, longDays, strikesLimit],
    queryFn: () => getGEXDashboardView(symbol, { historyDays, longDays, strikesLimit }),
    staleTime: 60_000,
    enabled,
    retry: 1,
  });
}

export function useGEXLatest(symbol: GEXSymbol) {
  return useQuery({
    queryKey: ['gex', 'latest', symbol],
    queryFn: () => getGEXLatest(symbol),
    staleTime: 60_000,
  });
}

export function useGEXStrikes(symbol: GEXSymbol, limit = 60) {
  return useQuery({
    queryKey: ['gex', 'strikes', symbol, limit],
    queryFn: () => getGEXStrikes(symbol, limit),
    staleTime: 120_000,
  });
}

export function useGEXHistory(days = 90) {
  return useQuery({
    queryKey: ['gex', 'history', days],
    queryFn: () => getGEXHistory(days),
    staleTime: 5 * 60_000,
  });
}

export function useGEXAlphaHistory(days = 90) {
  return useQuery({
    queryKey: ['gex', 'alpha-history', days],
    queryFn: () => getGEXAlphaHistory(days),
    staleTime: 5 * 60_000,
  });
}

/** 监听 GEXMETRIX_SNAPSHOT 推送，刷新 dashboard-view 与 summary */
export function useGEXWSSync(activeSymbol: GEXSymbol) {
  const qc = useQueryClient();
  const ws = useWebSocketContext();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  const queryKey = useMemo(() => ['gex', 'dashboard-view', activeSymbol], [activeSymbol]);

  useEffect(() => {
    if (!ws) return;
    const unsub = ws.subscribe((msg) => {
      const t =
        (msg as unknown as { topic?: string }).topic ??
        (msg as unknown as { type?: string }).type;
      const typeStr = typeof t === 'string' ? t : '';
      const payload = (msg as unknown as { payload?: { symbol?: string } }).payload;
      const symbol = payload?.symbol;
      if (
        typeStr === 'GEXMETRIX_SNAPSHOT' ||
        typeStr === 'DATA_FETCH_COMPLETE' ||
        typeStr === 'PIPELINE_CYCLE_COMPLETE'
      ) {
        qc.invalidateQueries({ queryKey: ['gex'] });
        const ts = msg.timestamp ?? new Date().toISOString();
        setLastUpdateAt(ts);
      } else if (symbol && symbol === activeSymbol && typeStr === 'GEX_UPDATE') {
        qc.invalidateQueries({ queryKey: queryKey });
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt, activeSymbol, queryKey]);
}
