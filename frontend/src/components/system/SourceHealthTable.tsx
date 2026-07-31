/**
 * Source Health Table — 23 fetchers 健康矩阵
 * 列表 + 过滤（all/online/degraded/offline/mock）
 */
import { useMemo, useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import type { SourceStatus } from '@/lib/api/types';
import { sourceLabel, sourceTone } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface Props {
  sources: SourceStatus[];
  loading?: boolean;
}

type Filter = 'all' | 'online' | 'degraded' | 'offline' | 'mock';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'online', label: '在线' },
  { value: 'degraded', label: '降级' },
  { value: 'offline', label: '离线' },
  { value: 'mock', label: 'Mock' },
];

export function SourceHealthTable({ sources, loading }: Props) {
  const [filter, setFilter] = useState<Filter>('all');

  const filtered = useMemo(() => {
    if (filter === 'all') return sources;
    if (filter === 'mock') return sources.filter((s) => s.is_mock);
    return sources.filter((s) => s.status === filter);
  }, [sources, filter]);

  const counts = useMemo(() => {
    const c = { all: sources.length, online: 0, degraded: 0, offline: 0, mock: 0 };
    sources.forEach((s) => {
      if (s.is_mock) c.mock += 1;
      if (s.status === 'online') c.online += 1;
      if (s.status === 'degraded') c.degraded += 1;
      if (s.status === 'offline') c.offline += 1;
    });
    return c;
  }, [sources]);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">数据源健康矩阵</h3>
            <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
              {sources.length} fetchers
            </span>
          </div>
          <div className="flex items-center gap-1" role="tablist" aria-label="数据源过滤">
            {FILTERS.map((f) => {
              const count = counts[f.value];
              const active = filter === f.value;
              return (
                <button
                  key={f.value}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setFilter(f.value)}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]',
                    active
                      ? 'bg-[var(--color-primary)]/15 text-[var(--color-primary)]'
                      : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]',
                  )}
                >
                  {f.label}
                  <span className="text-[10px] opacity-70 font-mono">{count}</span>
                </button>
              );
            })}
          </div>
        </div>

        {loading && sources.length === 0 ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-7 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-[120px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            无匹配数据源
          </div>
        ) : (
          <div
            role="table"
            aria-label="数据源健康表"
            className="overflow-x-auto -mx-2"
          >
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <th className="px-2 py-2 font-medium">Name</th>
                  <th className="px-2 py-2 font-medium">Status</th>
                  <th className="px-2 py-2 font-medium text-right">Avail</th>
                  <th className="px-2 py-2 font-medium text-right">Rows</th>
                  <th className="px-2 py-2 font-medium">Last Data</th>
                  <th className="px-2 py-2 font-medium">Mock?</th>
                  <th className="px-2 py-2 font-medium">Error</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => {
                  const tone = sourceTone(s.status, s.is_mock, Boolean(s.last_error));
                  const dotClass =
                    tone === 'success'
                      ? 'bg-[var(--color-success)]'
                      : tone === 'warning'
                        ? 'bg-[var(--color-warning)]'
                        : tone === 'danger'
                          ? 'bg-[var(--color-danger)]'
                          : 'bg-[var(--color-text-muted)]';
                  return (
                    <tr
                      key={s.name}
                      className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-elevated)]/50"
                    >
                      <td className="px-2 py-1.5 font-mono text-[var(--color-text-primary)]">
                        <div className="flex items-center gap-2">
                          <span aria-hidden className={cn('inline-block w-1.5 h-1.5 rounded-full', dotClass)} />
                          <span className="font-semibold">{s.name}</span>
                          {s.method && (
                            <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
                              {s.method}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-2 py-1.5">
                        <span
                          className={cn(
                            'inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase',
                            tone === 'success' && 'bg-[var(--color-success)]/15 text-[var(--color-success)]',
                            tone === 'warning' && 'bg-[var(--color-warning)]/15 text-[var(--color-warning)]',
                            tone === 'danger' && 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]',
                            tone === 'neutral' && 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]',
                          )}
                          aria-label={sourceLabel(tone)}
                        >
                          {sourceLabel(tone)}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono">
                        {(s.availability_pct ?? 0).toFixed(1)}%
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono">
                        {(s.total_rows ?? 0).toLocaleString()}
                      </td>
                      <td className="px-2 py-1.5 font-mono text-[var(--color-text-muted)]">
                        {s.last_data_ts
                          ? new Date(s.last_data_ts).toLocaleString('zh-CN', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>
                      <td className="px-2 py-1.5">
                        {s.is_mock ? (
                          <span className="inline-block px-1.5 py-0.5 rounded bg-[var(--color-warning)]/15 text-[var(--color-warning)] text-[10px] font-bold">
                            {s.mock_reason ?? 'MOCK'}
                          </span>
                        ) : (
                          <span className="text-[10px] text-[var(--color-text-muted)]">—</span>
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-[var(--color-danger)] truncate max-w-[200px]" title={s.last_error ?? undefined}>
                        {s.last_error ?? <span className="text-[var(--color-text-muted)]">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}