/**
 * TanStack Query hooks — VIX
 * 端点（与 backend/api/routes/vix.py 对齐）：
 * - GET /api/vix/latest                 VIX 最新 row
 * - GET /api/vix/term-structure         期限结构（含 panic_premium）
 * - GET /api/vix/history?days=90        VIX 历史
 * - GET /api/vix/term-structure-history 期限结构历史
 *
 * 监听 WS：
 * - DATA_FETCH_COMPLETE / PIPELINE_CYCLE_COMPLETE → 失效 vix keys
 */
import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getVIXLatest,
  getVIXTermStructure,
  getVIXHistory,
  getVIXTermStructureHistory,
} from '@/lib/api/vix';
import { useUIStore } from '@/lib/stores/ui';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

export function useVIXLatest() {
  return useQuery({
    queryKey: ['vix', 'latest'],
    queryFn: getVIXLatest,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useVIXTermStructure() {
  return useQuery({
    queryKey: ['vix', 'term-structure'],
    queryFn: getVIXTermStructure,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useVIXHistory(days = 90) {
  return useQuery({
    queryKey: ['vix', 'history', days],
    queryFn: () => getVIXHistory(days),
    staleTime: 5 * 60_000,
  });
}

export function useVIXTermStructureHistory(days = 365) {
  return useQuery({
    queryKey: ['vix', 'term-structure-history', days],
    queryFn: () => getVIXTermStructureHistory(days),
    staleTime: 5 * 60_000,
  });
}

export function useVIXWSSync() {
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
        typeStr === 'SCORING_COMPLETE'
      ) {
        qc.invalidateQueries({ queryKey: ['vix'] });
        const ts = msg.timestamp ?? new Date().toISOString();
        setLastUpdateAt(ts);
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt]);
}
