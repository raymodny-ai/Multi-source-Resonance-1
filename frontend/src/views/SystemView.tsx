/**
 * System 页面（健康 / 诊断 / 控制）
 * PRD §4.8
 *
 * Layout:
 * - Header metrics (4 卡): Uptime / Version / Pipeline / Last Cycle
 * - Source Health Table (filter tabs)
 * - Collection Report (left) | System Control (right)
 * - Prometheus Metrics Summary (left) | System Logs (right)
 */
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { SystemHeaderMetricsCard } from '@/components/system/SystemHeaderMetricsCard';
import { SourceHealthTable } from '@/components/system/SourceHealthTable';
import { CollectionReportCard } from '@/components/system/CollectionReportCard';
import { SystemControlCard } from '@/components/system/SystemControlCard';
import { MetricsSummaryCard, PrometheusRawCard } from '@/components/system/MetricsCards';
import { SystemLogsCard } from '@/components/system/SystemLogsCard';
import {
  useCollectionDetail,
  useMetricsSummary,
  useSourceStatus,
  useSystemStatus,
  useSystemWSSync,
} from '@/lib/hooks/useSystem';
import { useUIStore } from '@/lib/stores/ui';

export function SystemView() {
  useSystemWSSync();
  const qc = useQueryClient();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);

  const status = useSystemStatus();
  const sources = useSourceStatus();
  const collection = useCollectionDetail();
  const metrics = useMetricsSummary();

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: ['system'] });
    qc.invalidateQueries({ queryKey: ['metrics'] });
    setLastUpdateAt(new Date().toISOString());
  };

  const sourcesData = sources.data ?? [];
  const offlineCount = sourcesData.filter((s) => s.status === 'offline').length;
  const mockCount = sourcesData.filter((s) => s.is_mock).length;

  return (
    <>
      <PageHeader
        title="System"
        description="健康 / 诊断 / 控制 · Pipeline + 23 fetchers + Prometheus"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {(status.error || sources.error || collection.error) && (
        <AlertBanner tone="danger" title="System 数据加载失败">
          {((status.error ?? sources.error ?? collection.error) as Error)?.message ?? '未知错误'}
        </AlertBanner>
      )}

      {(offlineCount > 0 || mockCount > 3) && (
        <AlertBanner tone="warning" title="检测到异常数据源" className="mt-2" dismissible>
          当前有 <strong>{offlineCount}</strong> 个离线数据源，
          <strong>{mockCount}</strong> 个 Mock 数据源（建议检查 API Key 或网络）。
        </AlertBanner>
      )}

      {/* Header metrics */}
      <div className="mt-4">
        <SystemHeaderMetricsCard
          status={status.data ?? null}
          metrics={metrics.data ?? null}
          collection={collection.data ?? null}
          loading={
            (status.isLoading && !status.data) ||
            (metrics.isLoading && !metrics.data) ||
            (collection.isLoading && !collection.data)
          }
        />
      </div>

      {/* Source health table */}
      <div className="mt-4">
        <SourceHealthTable sources={sourcesData} loading={sources.isLoading && sourcesData.length === 0} />
      </div>

      {/* Collection + Control */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <CollectionReportCard
          report={collection.data ?? null}
          loading={collection.isLoading && !collection.data}
        />
        <SystemControlCard />
      </div>

      {/* Metrics + Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <MetricsSummaryCard />
        <SystemLogsCard />
      </div>

      {/* Prometheus raw */}
      <div className="mt-4">
        <PrometheusRawCard />
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        端点 <span className="text-[var(--color-primary)]">/api/system/*</span> ·{' '}
        <span className="text-[var(--color-primary)]">/api/metrics</span> ·{' '}
        上次更新：
        {status.dataUpdatedAt ? new Date(status.dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}