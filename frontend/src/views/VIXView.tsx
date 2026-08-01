/**
 * VIX 页面 — 波动率期限结构与衍生指标
 * PRD §4.3
 *
 * Layout:
 * - Top: VIXMetricsCard (Spot / VX1 / VX2 / Term Ratio / Panic Premium) | TermStructureCard
 * - Middle: VIX History Chart
 */
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { useQueryClient } from '@tanstack/react-query';
import {
  useVIXLatest,
  useVIXTermStructure,
  useVIXHistory,
  useVIXTermStructureHistory,
  useVIXWSSync,
} from '@/lib/hooks/useVIX';
import { VIXMetricsCard } from '@/components/vix/VIXMetricsCard';
import { VIXTermStructureCard } from '@/components/vix/VIXTermStructureCard';
import { VIXHistoryChart } from '@/components/vix/VIXHistoryChart';
import { useUIStore } from '@/lib/stores/ui';

export function VIXView() {
  useVIXWSSync();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  const qc = useQueryClient();

  const latest = useVIXLatest();
  const term = useVIXTermStructure();
  const history = useVIXHistory(90);
  const termHistory = useVIXTermStructureHistory(365);

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: ['vix'] });
    setLastUpdateAt(new Date().toISOString());
  };

  const latestData = latest.data ?? null;
  const termData = term.data ?? null;

  function toNum(v: unknown): number | null {
    if (v === null || v === undefined) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  // 合并 latest 与 term-structure：优先 term_structure 的字段，缺失则用 latest
  const metrics =
    latestData || termData
      ? {
          vix_spot: toNum(termData?.vix_spot ?? latestData?.vix_spot),
          vx1: toNum(termData?.vx1 ?? latestData?.vx1),
          vx2: toNum(termData?.vx2 ?? latestData?.vx2),
          term_structure_ratio: toNum(termData?.term_structure_ratio ?? latestData?.term_structure_ratio),
          term_structure_state: (termData?.term_structure_state ?? latestData?.term_structure_state ?? null) as
            | 'contango'
            | 'backwardation'
            | 'flat'
            | null,
          panic_premium: toNum(termData?.panic_premium ?? latestData?.panic_premium),
          timestamp: (latestData?.timestamp ?? termData?.timestamp ?? null) as string | null,
        }
      : null;

  return (
    <>
      <PageHeader
        title="VIX"
        description="波动率期限结构 · Contango / Backwardation / 恐慌溢价"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {(latest.error || term.error) && (
        <AlertBanner tone="danger" title="VIX 数据加载失败">
          {((latest.error ?? term.error) as Error)?.message ?? '未知错误'}
        </AlertBanner>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <div className="lg:col-span-2">
          <VIXMetricsCard
            latest={metrics}
            loading={(latest.isLoading || term.isLoading) && !metrics}
          />
        </div>
        <VIXTermStructureCard
          vixSpot={metrics?.vix_spot ?? null}
          vx1={metrics?.vx1 ?? null}
          vx2={metrics?.vx2 ?? null}
          state={metrics?.term_structure_state ?? null}
          // FIX-35: forward the backend-canonical ratio. The card now
          // shows ``1 + term_structure_ratio`` so the chart and the
          // history card stay consistent (both use the fetcher's
          // ``vx_3m_proxy / vix_spot - 1`` definition).
          termStructureRatio={metrics?.term_structure_ratio ?? null}
          loading={term.isLoading && !termData}
        />
      </div>

      <div className="mt-4">
        <VIXHistoryChart
          history={history.data ?? []}
          termHistory={termHistory.data ?? []}
          loading={(history.isLoading && !history.data) || (termHistory.isLoading && !termHistory.data)}
          height={320}
        />
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        终态：{metrics?.term_structure_state ?? '—'} · Panic：
        {metrics?.panic_premium != null && Number.isFinite(metrics.panic_premium)
          ? (metrics.panic_premium as number).toFixed(3)
          : '—'} ·{' '}
        上次更新：{latest.dataUpdatedAt ? new Date(latest.dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}
