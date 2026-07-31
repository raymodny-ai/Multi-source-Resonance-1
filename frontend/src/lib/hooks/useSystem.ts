/**
 * TanStack Query hooks — System 健康 / 诊断
 * 与 backend/api/routes/system.py 对齐
 */
import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAutoPollingState,
  getCollectionDetail,
  getSourceStatusList,
  getSystemLogs,
  getSystemStatusInfo,
  setAutoPollingState,
  triggerManualCollection,
} from '@/lib/api/system';
import { getMetricsSummary, getPrometheusMetrics } from '@/lib/api/metrics';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';
import { useUIStore } from '@/lib/stores/ui';

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system', 'status'],
    queryFn: getSystemStatusInfo,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useSourceStatus() {
  return useQuery({
    queryKey: ['system', 'source-status'],
    queryFn: getSourceStatusList,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useCollectionDetail() {
  return useQuery({
    queryKey: ['system', 'collection-detail'],
    queryFn: getCollectionDetail,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useMetricsSummary() {
  return useQuery({
    queryKey: ['metrics', 'summary'],
    queryFn: getMetricsSummary,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function usePrometheusMetrics(enabled = false) {
  return useQuery({
    queryKey: ['metrics', 'prometheus'],
    queryFn: getPrometheusMetrics,
    staleTime: 15_000,
    refetchInterval: enabled ? 30_000 : false,
    enabled,
    retry: 0,
  });
}

export function useSystemLogs(limit = 50) {
  return useQuery({
    queryKey: ['system', 'logs', limit],
    queryFn: () => getSystemLogs(limit),
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useAutoPolling() {
  return useQuery({
    queryKey: ['system', 'auto-polling'],
    queryFn: getAutoPollingState,
    staleTime: 5_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useSetAutoPolling() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => setAutoPollingState(enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['system', 'auto-polling'] }),
  });
}

export function useManualCollect() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => triggerManualCollection(),
    onSuccess: () => {
      // 触发后刷新相关视图
      qc.invalidateQueries({ queryKey: ['system'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      qc.invalidateQueries({ queryKey: ['metrics'] });
    },
  });
}

/** 监听 WS 事件，刷新 system 视图 */
export function useSystemWSSync() {
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
        typeStr === 'PIPELINE_CYCLE_COMPLETE' ||
        typeStr === 'DATA_FETCH_COMPLETE' ||
        typeStr === 'DATA_MOCK_FALLBACK' ||
        typeStr === 'DATA_FETCH_ERROR'
      ) {
        qc.invalidateQueries({ queryKey: ['system'] });
        qc.invalidateQueries({ queryKey: ['metrics'] });
        const ts = msg.timestamp ?? new Date().toISOString();
        setLastUpdateAt(ts);
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt]);
}