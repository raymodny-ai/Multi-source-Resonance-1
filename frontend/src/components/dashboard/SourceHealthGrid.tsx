/**
 * 数据源健康网格
 * - 后端 /api/system/source-status 返回 list of SourceStatus（不含 mock_reason 默认字段）
 * - 这里收敛成统一类型 SourceStatus
 * - 颜色：绿=在线/橙=降级/红=离线/灰=未知
 */
import { useQuery } from '@tanstack/react-query';
import { getSourceStatusList } from '@/lib/api/system';
import { sourceLabel, sourceTone, type SourceStatusTone } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

const TONE_DOT: Record<SourceStatusTone, string> = {
  success: 'bg-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]',
  danger: 'bg-[var(--color-danger)]',
  neutral: 'bg-[var(--color-text-muted)]',
};

export function useSourceStatus() {
  return useQuery({
    queryKey: ['system', 'source-status'],
    queryFn: getSourceStatusList,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function SourceHealthGrid() {
  const { data, isLoading, error } = useSourceStatus();
  const sources = data ?? [];

  if (error && sources.length === 0) {
    return (
      <div className="msr-card">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">数据源健康</h3>
        </div>
        <div className="text-xs text-[var(--color-danger)] py-4">无法加载数据源健康: {(error as Error).message}</div>
      </div>
    );
  }

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
        {sources.map((s) => {
          const tone = sourceTone(s.status, s.is_mock, !!s.last_error);
          const mockTag = s.is_mock ? ' (MOCK)' : '';
          const errorTag = s.last_error ? ` · ${s.last_error}` : '';
          return (
            <div
              key={s.name}
              className="relative group aspect-square"
              title={`${s.name} · ${sourceLabel(tone)}${mockTag}${errorTag}`}
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
