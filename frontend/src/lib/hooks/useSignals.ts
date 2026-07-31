/**
 * TanStack Query hooks — Signals
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { acknowledgeSignal, getSignalsHistory } from '@/lib/api/signals';
import type { Signal, SignalLevelFilter, SignalOutcomeFilter } from '@/lib/api/types';
import { useEffect, useState } from 'react';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

export interface SignalFilters {
  level: SignalLevelFilter;
  outcome: SignalOutcomeFilter;
  search: string;
  startDate: string | null;
  endDate: string | null;
  page: number;
  limit: number;
}

export const defaultSignalFilters: SignalFilters = {
  level: 'all',
  outcome: 'all',
  search: '',
  startDate: null,
  endDate: null,
  page: 1,
  limit: 25,
};

export function useSignalsHistory(filters: SignalFilters) {
  return useQuery({
    queryKey: ['signals', 'history', filters],
    queryFn: () => getSignalsHistory({
      level: filters.level,
      outcome: filters.outcome,
      search: filters.search || undefined,
      startDate: filters.startDate ?? undefined,
      endDate: filters.endDate ?? undefined,
      page: filters.page,
      limit: filters.limit,
    }),
    staleTime: 10_000,
    placeholderData: (prev) => prev,
  });
}

export function useAcknowledgeSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: Signal['id']) => acknowledgeSignal(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

/** 监听 WS SIGNAL_ALERT 事件，刷新列表 */
export function useSignalsWSSync() {
  const qc = useQueryClient();
  const ws = useWebSocketContext();
  useEffect(() => {
    if (!ws) return;
    const unsub = ws.subscribe((msg) => {
      if (msg.type === 'SIGNAL_ALERT') {
        qc.invalidateQueries({ queryKey: ['signals'] });
      }
    });
    return unsub;
  }, [ws, qc]);
}

/** 本地分页 / 过滤 state hook（与 query 解耦） */
export function useSignalFiltersState(initial: Partial<SignalFilters> = {}) {
  const [filters, setFilters] = useState<SignalFilters>({ ...defaultSignalFilters, ...initial });
  const update = (patch: Partial<SignalFilters>) =>
    setFilters((f) => {
      // 任何过滤条件变化都重置到第 1 页（显式指定 page 时跳过）
      const next = { ...f, ...patch };
      if (!('page' in patch)) next.page = 1;
      return next;
    });
  const reset = () => setFilters({ ...defaultSignalFilters, ...initial });
  return { filters, setFilters, update, reset };
}