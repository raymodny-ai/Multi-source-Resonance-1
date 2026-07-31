/**
 * Signals 页面（信号历史 & 管理）
 * PRD §4.6
 * - SignalFiltersBar：过滤条件
 * - SignalTable：分页表格
 * - SignalDetailDrawer：详情
 * - AcknowledgeDialog：人工确认
 * - useSignalsWSSync：监听 SIGNAL_ALERT 实时刷新
 */
import { useCallback, useState } from 'react';
import {
  useSignalsHistory,
  useSignalsWSSync,
  useAcknowledgeSignal,
  useSignalFiltersState,
} from '@/lib/hooks/useSignals';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { SignalFiltersBar } from '@/components/signals/SignalFilters';
import { SignalTable, SignalTableSkeleton } from '@/components/signals/SignalTable';
import { SignalDetailDrawer } from '@/components/signals/SignalDetailDrawer';
import { AcknowledgeDialog } from '@/components/signals/AcknowledgeDialog';
import { Button } from 'sparkdesign';
import type { Signal } from '@/lib/api/types';
import { useUIStore } from '@/lib/stores/ui';

export function SignalsView() {
  useSignalsWSSync();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);

  const { filters, update, reset } = useSignalFiltersState();
  const { data, isLoading, error } = useSignalsHistory(filters);

  const ack = useAcknowledgeSignal();

  const [detailSignal, setDetailSignal] = useState<Signal | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [ackTarget, setAckTarget] = useState<Signal | null>(null);
  const [ackOpen, setAckOpen] = useState(false);

  const handleSelect = useCallback((signal: Signal) => {
    setDetailSignal(signal);
    setDrawerOpen(true);
  }, []);

  const handleAcknowledgeClick = useCallback((signal: Signal) => {
    setAckTarget(signal);
    setAckOpen(true);
  }, []);

  const handleConfirmAck = useCallback(
    async (signal: Signal) => {
      try {
        await ack.mutateAsync(signal.id);
        setAckOpen(false);
        setAckTarget(null);
        // Update local selected signal to reflect new acknowledged state
        setDetailSignal((prev) =>
          prev && prev.id === signal.id
            ? { ...prev, acknowledged: true, acknowledged_at: new Date().toISOString() }
            : prev,
        );
      } catch (e) {
        // ErrorToast 会通过 msr-api-error 事件自动处理
        console.error('Failed to acknowledge signal', e);
      }
    },
    [ack],
  );

  const handleRefresh = useCallback(() => {
    setLastUpdateAt(new Date().toISOString());
  }, [setLastUpdateAt]);

  const rows = data?.data ?? [];
  const total = data?.total ?? 0;
  const page = filters.page;
  const limit = filters.limit;

  return (
    <>
      <PageHeader
        title="Signals"
        description="历史警报记录、确认与回溯分析"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {error && (
        <AlertBanner tone="danger" title="无法加载 Signals 历史">
          {(error as Error).message}
        </AlertBanner>
      )}

      <div className="space-y-4 mt-2">
        <SignalFiltersBar filters={filters} update={update} reset={reset} />

        {isLoading && rows.length === 0 ? (
          <SignalTableSkeleton />
        ) : (
          <SignalTable
            rows={rows}
            total={total}
            page={page}
            limit={limit}
            loading={isLoading}
            selectedId={detailSignal?.id ?? null}
            onSelect={handleSelect}
            onPageChange={(p) => update({ page: p })}
          />
        )}
      </div>

      <SignalDetailDrawer
        signal={detailSignal}
        open={drawerOpen}
        onOpenChange={(o) => {
          setDrawerOpen(o);
          if (!o) setDetailSignal(null);
        }}
        onAcknowledge={handleAcknowledgeClick}
        acknowledging={ack.isPending}
      />

      <AcknowledgeDialog
        signal={ackTarget}
        open={ackOpen}
        onOpenChange={setAckOpen}
        onConfirm={handleConfirmAck}
        confirming={ack.isPending}
      />
    </>
  );
}
