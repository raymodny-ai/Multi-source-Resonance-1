/**
 * TanStack Query hooks — Dark Pool / DIX
 * 端点：
 * - GET /api/darkpool/latest     dark_pool_metrics latest
 * - GET /api/darkpool/flow       dark_pool_flow_history 表
 * - GET /api/darkpool/history    dark_pool_metrics 历史
 * - GET /api/darkpool/history-intraday intraday 数据（与 SPX 价格合并）
 */
import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getDarkpoolLatest,
  getDarkpoolFlow,
  getDarkpoolHistory,
  getDarkpoolHistoryIntraday,
} from '@/lib/api/darkpool';
import { useUIStore } from '@/lib/stores/ui';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

export function useDarkpoolLatest() {
  return useQuery({
    queryKey: ['darkpool', 'latest'],
    queryFn: getDarkpoolLatest,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useDarkpoolFlow(days = 30) {
  return useQuery({
    queryKey: ['darkpool', 'flow', days],
    queryFn: () => getDarkpoolFlow(days),
    staleTime: 5 * 60_000,
  });
}

export function useDarkpoolHistory(days = 90) {
  return useQuery({
    queryKey: ['darkpool', 'history', days],
    queryFn: () => getDarkpoolHistory(days),
    staleTime: 5 * 60_000,
  });
}

export function useDarkpoolHistoryIntraday(days = 30) {
  return useQuery({
    queryKey: ['darkpool', 'history-intraday', days],
    queryFn: () => getDarkpoolHistoryIntraday(days),
    staleTime: 60_000,
  });
}

export function useDarkpoolWSSync() {
  const qc = useQueryClient();
  const ws = useWebSocketContext();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  useEffect(() => {
    if (!ws) return;
    const unsub = ws.subscribe((msg) => {
      const t =
        (msg as unknown as { topic?: string }).topic ??
        (msg as unknown as { type?: string }).type;
      const typeStr = typeof t === 'string' ? t : '';
      if (
        typeStr === 'DATA_FETCH_COMPLETE' ||
        typeStr === 'PIPELINE_CYCLE_COMPLETE' ||
        typeStr === 'DARKPOOL_UPDATE'
      ) {
        qc.invalidateQueries({ queryKey: ['darkpool'] });
        const ts = msg.timestamp ?? new Date().toISOString();
        setLastUpdateAt(ts);
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt]);
}
