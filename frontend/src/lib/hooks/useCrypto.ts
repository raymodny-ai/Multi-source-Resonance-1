/**
 * TanStack Query hooks — Crypto Derivatives
 * 字段以 crypto_derivatives 表为准（btc_funding_rate / btc_oi）
 *
 * 监听：
 * - DATA_FETCH_COMPLETE / PIPELINE_CYCLE_COMPLETE 失效
 */
import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCryptoLatest, getCryptoHistory } from '@/lib/api/crypto';
import { useUIStore } from '@/lib/stores/ui';
import { useWebSocketContext } from '@/lib/ws/WebSocketProvider';

export function useCryptoLatest() {
  return useQuery({
    queryKey: ['crypto', 'latest'],
    queryFn: getCryptoLatest,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useCryptoHistory(days = 30) {
  return useQuery({
    queryKey: ['crypto', 'history', days],
    queryFn: () => getCryptoHistory(days),
    staleTime: 5 * 60_000,
  });
}

export function useCryptoWSSync() {
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
        typeStr === 'CRYPTO_UPDATE'
      ) {
        qc.invalidateQueries({ queryKey: ['crypto'] });
        const ts = msg.timestamp ?? new Date().toISOString();
        setLastUpdateAt(ts);
      }
    });
    return unsub;
  }, [ws, qc, setLastUpdateAt]);
}
