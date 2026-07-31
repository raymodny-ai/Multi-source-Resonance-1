/**
 * GEX 页面 — 期权 Gamma Exposure 详情
 * PRD §4.2
 *
 * Layout:
 * - Header (PageHeader) + 符号 Tabs (6 symbols)
 * - Top row: GEX KeyLevels (Call/Put Wall, Zero Gamma) | GEXSummary (compact)
 * - Middle row: GEX History chart (Net GEX + Spot overlay)
 * - Bottom row: GEX Strikes 分布图 (Call/Put GEX bars)
 * - Footer: GEXSummaryGrid (全部符号总览)
 */
import { useState } from 'react';
import { GEXSymbolTabs } from '@/components/gex/GEXSymbolTabs';
import { GEXKeyLevelsCard } from '@/components/gex/GEXKeyLevelsCard';
import { GEXHistoryChart, GEXHistoryChartEmpty, GEXHistoryChartSkeleton } from '@/components/gex/GEXHistoryChart';
import { GEXStrikesChart } from '@/components/gex/GEXStrikesChart';
import { GEXSymbolSummaryGrid } from '@/components/gex/GEXSymbolSummaryGrid';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { useGEXDashboardView, useGEXSummary, useGEXWSSync, type GEXSymbol } from '@/lib/hooks/useGEX';
import { useUIStore } from '@/lib/stores/ui';
import { Button } from 'sparkdesign';
import type { GEXDashboardView } from '@/lib/api/types';
import { fmtClock, fmtRelative } from '@/lib/utils/format';

export function GEXView() {
  const [active, setActive] = useState<GEXSymbol>('SPX');
  useGEXWSSync(active);
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);

  const { data, isLoading, error, dataUpdatedAt, refetch } = useGEXDashboardView(active, {
    historyDays: 7,
    longDays: 90,
    strikesLimit: 60,
  });

  const summary = useGEXSummary();

  const view = data as GEXDashboardView | undefined;
  const spot = view?.levels?.spot_price ?? view?.latest?.spot_price ?? null;
  const callWall = view?.levels?.call_wall ?? view?.latest?.call_wall ?? null;
  const putWall = view?.levels?.put_wall ?? view?.latest?.put_wall ?? null;
  const zeroGamma = view?.levels?.zero_gamma_level ?? view?.latest?.zero_gamma_level ?? null;

  const onRefresh = () => {
    refetch();
    setLastUpdateAt(new Date().toISOString());
  };

  return (
    <>
      <PageHeader
        title="GEX"
        description="期权 Gamma Exposure 分析 · Call/Put Wall 与净 GEX 走势"
        actions={
          <Button variant="outline" size="sm" onClick={onRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {error && (
        <AlertBanner tone="danger" title={`${active} 数据加载失败`}>
          {(error as Error).message}
        </AlertBanner>
      )}

      <div className="mt-2">
        <GEXSymbolTabs active={active} onChange={setActive} />
      </div>

      {/* Row 1: KeyLevels + Summary mini */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <GEXKeyLevelsCard
          spot={spot}
          callWall={callWall}
          putWall={putWall}
          zeroGammaLevel={zeroGamma}
          loading={isLoading && !data}
        />
        <div className="lg:col-span-2">
          <GEXHistoryChart
            history={view?.history ?? []}
            longHistory={view?.long_history ?? []}
            loading={isLoading && !data}
            height={260}
          />
        </div>
      </div>

      {/* Row 2: Strikes distribution */}
      <div className="mt-4">
        {isLoading && !data ? (
          <GEXHistoryChartSkeleton height={320} />
        ) : view?.strikes && view.strikes.strikes.length > 0 ? (
          <GEXStrikesChart
            strikes={view.strikes.strikes}
            spot={spot}
            callWall={callWall}
            putWall={putWall}
            height={340}
          />
        ) : (
          <GEXHistoryChartEmpty hint={`${active} Strike 分布数据为空`} />
        )}
      </div>

      {/* Row 3: Symbol summary */}
      <div className="mt-4">
        <GEXSymbolSummaryGrid
          rows={summary.data ?? []}
          active={active}
          onSelect={setActive}
          loading={summary.isLoading && !summary.data}
        />
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        当前符号 <span className="text-[var(--color-primary)] font-semibold">{active}</span> ·
        上次更新：
        {data?.fetched_at
          ? `${fmtClock(data.fetched_at)} · ${fmtRelative(data.fetched_at)}`
          : dataUpdatedAt
            ? new Date(dataUpdatedAt).toLocaleString('zh-CN')
            : '—'}
      </p>
    </>
  );
}
