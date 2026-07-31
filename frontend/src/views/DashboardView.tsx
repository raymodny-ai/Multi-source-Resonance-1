/**
 * Dashboard 页面（共振指挥中心）
 * PRD §4.1
 * - Hero: ResonanceGauge + 4 维度评分卡
 * - SignalTimeline (24h)
 * - HawkesIntensityCard + SourceHealthGrid
 */
import { useDashboard, useDashboardWSSync } from '@/lib/hooks/useDashboard';
import { ResonanceGauge } from '@/components/dashboard/ResonanceGauge';
import { DimensionScoreCards } from '@/components/dashboard/DimensionScoreCards';
import { SignalTimeline } from '@/components/dashboard/SignalTimeline';
import { HawkesIntensityCard } from '@/components/dashboard/HawkesIntensityCard';
import { SourceHealthGrid } from '@/components/dashboard/SourceHealthGrid';
import { DashboardSkeleton } from '@/components/dashboard/DashboardSkeleton';
import { AlertBanner } from '@/components/AlertBanner';
import { PageHeader } from '@/components/PageHeader';
import { useMemo } from 'react';
import { fmtClock, fmtRelative } from '@/lib/utils/format';

export function DashboardView() {
  useDashboardWSSync();
  const { data, isLoading, error, dataUpdatedAt } = useDashboard();

  const mockSources = data?.mock_sources ?? [];
  const alertLevel = data?.alert_level ?? null;

  const banner = useMemo(() => {
    if (error) {
      return (
        <AlertBanner tone="danger" title="无法加载 Dashboard 数据">
          后端连接失败，将显示缓存或占位数据。{(error as Error).message ?? ''}
        </AlertBanner>
      );
    }
    if (mockSources.length > 0) {
      return (
        <AlertBanner tone="warning" title="检测到模拟数据" dismissible>
          以下数据源当前为模拟值：<strong>{mockSources.join(', ')}</strong>。
          实际策略执行请以真实数据为准。
        </AlertBanner>
      );
    }
    if (alertLevel != null && alertLevel >= 2) {
      return (
        <AlertBanner tone={alertLevel >= 3 ? 'danger' : 'warning'} title={`当前警报等级 LEVEL ${alertLevel}`}>
          监控到强烈共振信号，建议立即在 Signals 页面查看明细。
        </AlertBanner>
      );
    }
    return null;
  }, [error, mockSources, alertLevel]);

  if (isLoading && !data) {
    return (
      <>
        <PageHeader title="Dashboard" description="综合共振指挥中心" />
        <DashboardSkeleton />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="综合共振指挥中心 · 实时跨维度信号聚合"
      />

      {banner}

      {/* Hero row: Gauge + Dimensions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <ResonanceGauge
          score={data?.resonance_score ?? null}
          alertLevel={alertLevel}
          loading={isLoading && !data}
        />
        <div className="lg:col-span-2">
          <DimensionScoreCards data={data} loading={isLoading && !data} />
        </div>
      </div>

      {/* Signal timeline */}
      <div className="mt-4">
        <SignalTimeline />
      </div>

      {/* Hawkes + Source Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <HawkesIntensityCard
          branchingRatio={data?.hawkes_branching_ratio ?? null}
          loading={isLoading && !data}
        />
        <div className="lg:col-span-2">
          <SourceHealthGrid />
        </div>
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        上次更新：
        {data?.last_cycle_at
          ? `${fmtClock(data.last_cycle_at)} · ${fmtRelative(data.last_cycle_at)}`
          : dataUpdatedAt
            ? new Date(dataUpdatedAt).toLocaleString('zh-CN')
            : '—'}
      </p>
    </>
  );
}
