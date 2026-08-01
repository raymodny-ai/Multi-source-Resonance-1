/**
 * TanStack Query hooks — Signals
 * 与 backend/api/routes/signals.py 一致：分页用 offset/limit；字段以 signal_alerts 表为准
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { acknowledgeSignal, getBayesianWeights, getSignalsHistory } from '@/lib/api/signals';
import type {
  PaginatedResponse,
  Signal,
  SignalLevelFilter,
  SignalOutcomeFilter,
} from '@/lib/api/types';
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
  return useQuery<PaginatedResponse<Signal>>({
    queryKey: ['signals', 'history', filters],
    queryFn: () =>
      getSignalsHistory({
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
      const t =
        (msg as unknown as { topic?: string }).topic ??
        (msg as unknown as { type?: string }).type;
      const typeStr = typeof t === 'string' ? t : '';
      if (typeStr === 'SIGNAL_ALERT' || typeStr === 'SIGNAL_GENERATED' || typeStr === 'SIGNAL') {
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
      const next = { ...f, ...patch };
      if (!('page' in patch)) next.page = 1;
      return next;
    });
  const reset = () => setFilters({ ...defaultSignalFilters, ...initial });
  return { filters, setFilters, update, reset };
}

/** Adaptive Bayesian weight state + learning progress (IMPL-BAYESIAN-001 #4). */
export function useBayesianWeights(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['signals', 'bayesian-weights'],
    queryFn: () => getBayesianWeights(),
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 1,
    enabled: options?.enabled ?? true,
  });
}
