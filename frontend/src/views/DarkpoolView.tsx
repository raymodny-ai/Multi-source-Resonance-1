/**
 * Dark Pool 页面 — 暗池机构流动监控
 * PRD §4.5
 *
 * Layout:
 * - Top: DarkpoolMetricsCard (DIX + Short Ratio + Slope + signals)
 * - Middle: DarkpoolHistoryChart (DIX + EMA crossover + aggregated signals)
 * - Bottom: 30天 flow 列表（含日期 / dix / v_net / ema_fast / signals）
 */
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { Card, CardContent } from 'sparkdesign';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from 'sparkdesign';
import { DarkpoolMetricsCard } from '@/components/darkpool/DarkpoolMetricsCard';
import { DarkpoolHistoryChart } from '@/components/darkpool/DarkpoolHistoryChart';
import {
  useDarkpoolFlow,
  useDarkpoolHistory,
  useDarkpoolLatest,
  useDarkpoolWSSync,
} from '@/lib/hooks/useDarkpool';
import { useQueryClient } from '@tanstack/react-query';
import { useUIStore } from '@/lib/stores/ui';
import { fmtNum, fmtTime } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

// FIX-49: helper that joins a date with a time portion only when the
// input lacks one. ``r.date`` is a SQL DATE (YYYY-MM-DD), but the API
// may eventually return full timestamps in the same field — appending
// ``T00:00:00`` twice produces "2026-07-31T00:00:00T00:00:00" which
// ``new Date(...)`` parses as Invalid Date.
function joinDateTime(date: string): string {
  if (!date) return date;
  if (/T/.test(date)) return date;
  return `${date}T00:00:00`;
}

const DAY_OPTIONS = [
  { value: '30', label: '最近 30 天' },
  { value: '60', label: '最近 60 天' },
  { value: '90', label: '最近 90 天' },
  { value: '180', label: '最近 180 天' },
] as const;

export function DarkpoolView() {
  useDarkpoolWSSync();
  const qc = useQueryClient();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  const [days, setDays] = useState<string>('90');

  const latest = useDarkpoolLatest();
  const history = useDarkpoolHistory(Number(days));
  const flow = useDarkpoolFlow(30);

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: ['darkpool'] });
    setLastUpdateAt(new Date().toISOString());
  };

  return (
    <>
      <PageHeader
        title="Dark Pool"
        description="暗池机构流动监控 · DIX / Short Ratio / 聚合信号"
        actions={
          <>
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DAY_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
              刷新
            </Button>
          </>
        }
      />

      {latest.error && (
        <AlertBanner tone="danger" title="Darkpool 数据加载失败">
          {(latest.error as Error).message}
        </AlertBanner>
      )}

      <div className="mt-4">
        <DarkpoolMetricsCard latest={latest.data ?? null} loading={latest.isLoading && !latest.data} />
      </div>

      <div className="mt-4">
        <DarkpoolHistoryChart
          history={history.data ?? []}
          loading={history.isLoading && !history.data}
          height={300}
        />
      </div>

      {/* Flow list */}
      <div className="mt-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">最近 30 天流量</h3>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                {(flow.data ?? []).length} 条
              </span>
            </div>
            {flow.isLoading && !flow.data ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-8 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
                ))}
              </div>
            ) : !flow.data || flow.data.length === 0 ? (
              <div className="h-[100px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
                无流量数据
              </div>
            ) : (
              <ul className="space-y-0 max-h-[280px] overflow-y-auto pr-2">
                {flow.data.map((r, idx) => (
                  <li
                    key={`${r.date}-${idx}`}
                    className={cn(
                      'grid grid-cols-4 gap-2 border-t border-[var(--color-border)] py-1.5 text-xs',
                      r.aggregated_signal && 'bg-[var(--color-warning)]/8',
                    )}
                  >
                    <span className="font-mono text-[var(--color-text-muted)]">{fmtTime(joinDateTime(r.date))}</span>
                    <span className="font-mono text-right">{fmtNum(r.dix_value, 3)}</span>
                    <span className={cn('font-mono text-right', (r.v_net ?? 0) > 0 ? 'text-[var(--color-success)]' : (r.v_net ?? 0) < 0 ? 'text-[var(--color-danger)]' : '')}>
                      {fmtNum(r.v_net, 2)}
                    </span>
                    <span className="flex items-center justify-end gap-1">
                      {r.aggregated_signal && (
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-danger)]" aria-label="聚合信号触发" />
                      )}
                      {r.zero_cross_signal ? (
                        <span className="text-[10px] font-bold text-[var(--color-info)]">{r.zero_cross_signal}</span>
                      ) : (
                        <span className="text-[10px] text-[var(--color-text-muted)]">—</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        数据源 <span className="text-[var(--color-primary)] font-semibold">FINRA ADF / Stockgrid / DBMF / ChartExchange</span> ·
        上次更新：{latest.dataUpdatedAt ? new Date(latest.dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}
