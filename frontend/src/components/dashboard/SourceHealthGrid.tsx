/**
 * 数据源健康网格
 * - 23 个 fetcher 的状态点阵
 * - 颜色：绿=在线/橙=降级/红=离线/灰=未知
 */
import { useQuery } from '@tanstack/react-query';
import { getSystemHealth } from '@/lib/api/system';
import { sourceLabel, sourceTone, type SourceStatusTone } from '@/lib/utils/format';
import type { SourceStatus } from '@/lib/api/types';
import { cn } from '@/lib/utils/cn';

const TONE_DOT: Record<SourceStatusTone, string> = {
  success: 'bg-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]',
  danger: 'bg-[var(--color-danger)]',
  neutral: 'bg-[var(--color-text-muted)]',
};

export function useSystemHealthQuery() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: getSystemHealth,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function SourceHealthGrid() {
  const { data, isLoading } = useSystemHealthQuery();
  const sources = data?.sources ?? [];

  if (isLoading && sources.length === 0) {
    return (
      <div className="msr-card">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">数据源健康</h3>
        </div>
        <div className="grid grid-cols-12 gap-1.5">
          {Array.from({ length: 23 }).map((_, i) => (
            <div key={i} className="aspect-square rounded bg-[var(--color-border)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="msr-card flex flex-col gap-2" role="group" aria-label="数据源健康状态">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">数据源健康 · {sources.length} 源</h3>
        <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
          {(['success', 'warning', 'danger'] as SourceStatusTone[]).map((t) => (
            <span key={t} className="flex items-center gap-1">
              <span className={cn('inline-block h-2 w-2 rounded-full', TONE_DOT[t])} aria-hidden />
              {sourceLabel(t)}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-1.5">
        {sources.map((s: SourceStatus) => {
          const tone = sourceTone(s.status, s.is_mock, !!s.last_error);
          return (
            <div
              key={s.name}
              className="relative group aspect-square"
              title={`${s.name} · ${sourceLabel(tone)}${s.is_mock ? ' (MOCK)' : ''}${s.last_error ? ` · ${s.last_error}` : ''}`}
            >
              <div className={cn('absolute inset-0 rounded', TONE_DOT[tone])} aria-hidden />
              <span className="sr-only">{`${s.name} 状态 ${sourceLabel(tone)}`}</span>
            </div>
          );
        })}
      </div>

      {sources.length === 0 && (
        <div className="text-xs text-[var(--color-text-muted)] text-center py-4">暂无源状态</div>
      )}
    </div>
  );
}
