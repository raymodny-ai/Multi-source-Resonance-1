/**
 * TanStack Query hooks — Dashboard 数据
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDashboard, getDataQuality, getLatestSignal } from '@/lib/api/dashboard';
import type { DashboardData, Signal } from '@/lib/api/types';
import { useEffect } from 'react';
import { useUIStore } from '@/lib/stores/ui';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

const DASHBOARD_KEY = ['dashboard'] as const;
const LATEST_SIGNAL_KEY = ['signal', 'latest'] as const;
const DATA_QUALITY_KEY = ['dashboard', 'data-quality'] as const;

export function useDashboard(): ReturnType<typeof useQuery<DashboardData>> {
  return useQuery<DashboardData>({
    queryKey: DASHBOARD_KEY,
    queryFn: getDashboard,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useLatestSignal(): ReturnType<typeof useQuery<Signal | null>> {
  return useQuery<Signal | null>({
    queryKey: LATEST_SIGNAL_KEY,
    queryFn: getLatestSignal,
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useDataQuality() {
  return useQuery({
    queryKey: DATA_QUALITY_KEY,
    queryFn: getDataQuality,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

/** 监听 WS 事件，实时刷新 dashboard */
export function useDashboardWSSync() {
  const qc = useQueryClient();
  const ws = useWebSocketContext();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);

  useEffect(() => {
    if (!ws) return;
    const unsub = ws.subscribe((msg) => {
      if (msg.type === 'SCORING_COMPLETE' || msg.type === 'PIPELINE_CYCLE_COMPLETE') {
        qc.invalidateQueries({ queryKey: DASHBOARD_KEY });
        qc.invalidateQueries({ queryKey: LATEST_SIGNAL_KEY });
        qc.invalidateQueries({ queryKey: DATA_QUALITY_KEY });
        if (msg.timestamp) setLastUpdateAt(msg.timestamp);
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt]);
}