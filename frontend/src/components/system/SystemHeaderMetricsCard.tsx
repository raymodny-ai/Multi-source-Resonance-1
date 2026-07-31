/**
 * System Header 4 卡（Uptime / Version / Pipeline / Last Cycle）
 */
import { Card, CardContent } from 'sparkdesign';
import { fmtClock, fmtRelative } from '@/lib/utils/format';
import type { MetricsSummary, SystemStatusInfo } from '@/lib/api/types';
import type { CollectionReport } from '@/lib/api/types';

interface Props {
  status: SystemStatusInfo | null;
  metrics: MetricsSummary | null;
  collection: CollectionReport | null;
  loading?: boolean;
}

function SkeletonTile() {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="h-3 w-20 bg-[var(--color-border)] rounded animate-pulse mb-2" />
        <div className="h-7 w-32 bg-[var(--color-bg-elevated)] rounded animate-pulse" />
      </CardContent>
    </Card>
  );
}

function fmtUptime(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function TonalDot({ tone }: { tone: 'success' | 'warning' | 'danger' | 'neutral' }) {
  const map = {
    success: 'bg-[var(--color-success)]',
    warning: 'bg-[var(--color-warning)]',
    danger: 'bg-[var(--color-danger)]',
    neutral: 'bg-[var(--color-text-muted)]',
  } as const;
  return (
    <span
      aria-hidden
      className={`inline-block w-2 h-2 rounded-full ${map[tone]} ${tone === 'success' ? 'animate-pulse-dot' : ''}`}
    />
  );
}

export function SystemHeaderMetricsCard({ status, metrics, collection, loading }: Props) {
  if (loading && !status && !metrics) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonTile key={i} />
        ))}
      </div>
    );
  }

  const pipelineRunning = metrics?.pipeline?.running ?? false;
  const cycleTs = collection?.cycle_ts ?? null;
  const cycleNum = collection?.cycle_number ?? null;
  const fetchers = metrics?.pipeline?.fetchers ?? null;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {/* Uptime */}
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            Uptime
          </div>
          <div className="msr-number text-xl">{fmtUptime(status?.uptime_seconds ?? null)}</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            {status?.python_version ?? '—'}
          </div>
        </CardContent>
      </Card>

      {/* Version */}
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            Version
          </div>
          <div className="msr-number text-xl">v4.0.0</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            {status?.platform ?? '—'}
          </div>
        </CardContent>
      </Card>

      {/* Pipeline */}
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            Pipeline
          </div>
          <div className="flex items-center gap-2 mt-1">
            <TonalDot tone={pipelineRunning ? 'success' : 'neutral'} />
            <span
              className={`msr-number text-base font-bold ${
                pipelineRunning ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'
              }`}
              aria-label={pipelineRunning ? '运行中' : '已停止'}
            >
              {pipelineRunning ? 'RUNNING' : 'IDLE'}
            </span>
          </div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            {fetchers != null ? `${fetchers} fetchers` : '—'}
          </div>
        </CardContent>
      </Card>

      {/* Last Cycle */}
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            Last Cycle
          </div>
          <div className="msr-number text-xl">{cycleTs ? fmtClock(cycleTs) : '—'}</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            {cycleTs ? `${fmtRelative(cycleTs)} · #${cycleNum}` : '尚未运行'}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}