/**
 * CollectionReportCard — 上一个 pipeline cycle 的 per-source 报告
 */
import { Card, CardContent } from 'sparkdesign';
import type { CollectionReport } from '@/lib/api/types';
import { fmtTime } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface Props {
  report: CollectionReport | null;
  loading?: boolean;
}

export function CollectionReportCard({ report, loading }: Props) {
  if (loading && !report) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-40 bg-[var(--color-border)] rounded animate-pulse mb-3" />
          <div className="h-[180px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card>
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold mb-2">采集报告</h3>
          <div className="h-[120px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            尚无 cycle 报告
          </div>
        </CardContent>
      </Card>
    );
  }

  const total = report.sources.length;
  const success = report.success_count;
  const error = report.error_count;
  const mock = report.mock_count;
  const successPct = total > 0 ? (success / total) * 100 : 0;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">采集报告 · 最近一次</h3>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            cycle #{report.cycle_number} · {report.cycle_ts ? fmtTime(report.cycle_ts) : '—'}
          </span>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5 text-center">
            <div className="text-[10px] text-[var(--color-text-muted)]">成功</div>
            <div className="msr-number text-sm text-[var(--color-success)]">{success}</div>
          </div>
          <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5 text-center">
            <div className="text-[10px] text-[var(--color-text-muted)]">错误</div>
            <div className="msr-number text-sm text-[var(--color-danger)]">{error}</div>
          </div>
          <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5 text-center">
            <div className="text-[10px] text-[var(--color-text-muted)]">Mock</div>
            <div className="msr-number text-sm text-[var(--color-warning)]">{mock}</div>
          </div>
          <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5 text-center">
            <div className="text-[10px] text-[var(--color-text-muted)]">合计</div>
            <div className="msr-number text-sm">{total}</div>
          </div>
        </div>

        {/* Success bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-[var(--color-text-muted)]">成功率</span>
            <span className="text-[10px] font-mono font-semibold">{successPct.toFixed(1)}%</span>
          </div>
          <div className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-success)] transition-all duration-500"
              style={{ width: `${successPct}%` }}
              role="progressbar"
              aria-valuenow={successPct}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>

        {/* Per-source list */}
        <div className="max-h-[200px] overflow-y-auto pr-2">
          <ul className="space-y-0.5">
            {report.sources.map((s) => {
              const ok = !s.error;
              const tone = s.is_mock
                ? 'warning'
                : ok
                  ? 'success'
                  : 'danger';
              return (
                <li
                  key={s.source}
                  className="flex items-center justify-between text-xs border-t border-[var(--color-border)]/50 py-1 first:border-t-0"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      aria-hidden
                      className={cn(
                        'inline-block w-1.5 h-1.5 rounded-full shrink-0',
                        tone === 'success' && 'bg-[var(--color-success)]',
                        tone === 'warning' && 'bg-[var(--color-warning)]',
                        tone === 'danger' && 'bg-[var(--color-danger)]',
                      )}
                    />
                    <span className="font-mono truncate">{s.source}</span>
                    {s.is_mock && (
                      <span className="text-[9px] font-bold text-[var(--color-warning)]">MOCK</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)] font-mono shrink-0">
                    <span>{s.records_written ?? 0} rows</span>
                    <span>{(s.elapsed_sec ?? 0).toFixed(2)}s</span>
                    {s.retry_count > 0 && (
                      <span className="text-[var(--color-warning)]">retry ×{s.retry_count}</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}