/**
 * BayesianWeightsPanel — Bayesian 权重状态 + 重置
 */
import { useMemo } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { Button } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import { useMemo as useMemoReact } from 'react';
import { useResetWeights, useWeights } from '@/lib/hooks/useConfig';
import { cn } from '@/lib/utils/cn';

const DIM_COLORS: Record<string, string> = {
  gex: '#6366f1',
  vix: '#10b981',
  crypto: '#f59e0b',
  darkpool: '#ef4444',
};

export function BayesianWeightsPanel() {
  const { data, isLoading, error } = useWeights();
  const reset = useResetWeights();

  const dims = ['gex', 'vix', 'crypto', 'darkpool'];

  const chartOption = useMemoReact(() => {
    if (!data) return {};
    const weights = data.weights ?? {};
    const defaults = data.default_weights ?? {};
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['当前', '默认'], textStyle: { color: '#a0a0b5', fontSize: 11 } },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dims.map((d) => d.toUpperCase()),
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#a0a0b5', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#a0a0b5', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      },
      series: [
        {
          name: '当前',
          type: 'bar',
          data: dims.map((d) => ({
            value: weights[d] ?? 0,
            itemStyle: { color: DIM_COLORS[d] ?? '#6366f1' },
          })),
          barWidth: 20,
        },
        {
          name: '默认',
          type: 'bar',
          data: dims.map((d) => ({
            value: defaults[d] ?? 0,
            itemStyle: { color: DIM_COLORS[d] ?? '#6366f1', opacity: 0.4 },
          })),
          barWidth: 20,
        },
      ],
    };
  }, [data, dims]);

  const total = useMemo(
    () => (data ? Object.values(data.weights ?? {}).reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0) : 0),
    [data],
  );

  const handleReset = async () => {
    if (!confirm('确认重置 Bayesian 权重为默认值？')) return;
    try {
      await reset.mutateAsync();
    } catch {
      /* ErrorToast handles */
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Bayesian 权重</h3>
            {data?.is_adapted && (
              <span className="inline-block px-1.5 py-0.5 rounded bg-[var(--color-info)]/15 text-[var(--color-info)] text-[10px] font-bold">
                自适应
              </span>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={reset.isPending}
            aria-label="重置权重"
          >
            {reset.isPending ? '重置中...' : '重置为默认'}
          </Button>
        </div>

        {error && (
          <div className="text-xs text-[var(--color-danger)] py-2">
            权重加载失败：{(error as Error).message}
          </div>
        )}

        {isLoading && !data ? (
          <div className="h-[180px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        ) : data ? (
          <>
            <ReactECharts
              option={chartOption}
              style={{ height: 180, width: '100%' }}
              notMerge
              lazyUpdate
              opts={{ renderer: 'canvas' }}
            />
            <div className="grid grid-cols-2 gap-2 mt-3">
              {dims.map((d) => {
                const w = data.weights?.[d] ?? 0;
                const def = data.default_weights?.[d] ?? 0;
                const diff = w - def;
                return (
                  <div key={d} className="rounded bg-[var(--color-bg-elevated)] p-2">
                    <div className="flex items-center justify-between">
                      <div className="text-[10px] uppercase font-bold" style={{ color: DIM_COLORS[d] }}>
                        {d}
                      </div>
                      <div
                        className={cn(
                          'text-[10px] font-mono',
                          diff > 0 && 'text-[var(--color-success)]',
                          diff < 0 && 'text-[var(--color-danger)]',
                        )}
                      >
                        {diff > 0 ? '+' : ''}
                        {(diff * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="msr-number text-sm">{(w * 100).toFixed(1)}%</div>
                    <div className="text-[10px] text-[var(--color-text-muted)] font-mono">
                      default: {(def * 100).toFixed(1)}%
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-2 text-[10px] text-[var(--color-text-muted)] font-mono flex items-center justify-between">
              <span>raw_max: {data.raw_max?.toFixed(2) ?? '—'}</span>
              <span>合计: {total.toFixed(3)}</span>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}