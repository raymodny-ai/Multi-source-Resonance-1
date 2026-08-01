/**
 * BayesianWeightsPanel — Bayesian 权重状态 + 后验分布 / 可信区间 / 学习进度
 *
 * 数据源：GET /api/signals/bayesian-weights（IMPL-BAYESIAN-001 #4 可观测性）。
 * 相比旧 /api/config/weights 多返回：
 *   - posterior_summary[dim].credible_interval_95（95% 可信区间）
 *   - posterior_summary[dim].posterior_mean / posterior_std
 *   - update_count / last_update / decay_factor / min_outcomes
 *   - weight_delta（当前 − 默认）
 *   - persisted_state（证明权重重启存活）
 * 重置仍走旧 POST /api/config/weights/reset（useResetWeights）。
 */
import { useMemo } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { Button } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import { useResetWeights } from '@/lib/hooks/useConfig';
import { useBayesianWeights } from '@/lib/hooks/useSignals';
import { cn } from '@/lib/utils/cn';

const DIM_COLORS: Record<string, string> = {
  gex: '#6366f1',
  vix: '#10b981',
  crypto: '#f59e0b',
  darkpool: '#ef4444',
};

// FIX-47: lift ``DIMS`` out of the render so array identity is stable across
// renders (avoids invalidating useMemo on every render).
const DIMS: readonly string[] = Object.freeze(['gex', 'vix', 'crypto', 'darkpool']);

/** 从新 API 响应中取当前权重（兼容 current_weights 键）。 */
function currentWeightsOf(data: { current_weights?: Record<string, number> } | null | undefined): Record<string, number> {
  return data?.current_weights ?? {};
}

/** 后验均值再映射为 0-100 刻度（pct）。 */
const toWeightPct = (w: number | undefined) => ((w ?? 0) * 100).toFixed(1);

export function BayesianWeightsPanel() {
  const { data, isLoading, error } = useBayesianWeights();
  const reset = useResetWeights();

  const weights = currentWeightsOf(data);
  // 兼容：若后端回 default_weights；后验 summary 按 API 规范为 current_weight。
  const defaults = data?.default_weights ?? {};
  const posterior = data?.posterior_summary ?? {};

  const chartOption = useMemo(() => {
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['当前', '默认'], textStyle: { color: '#a0a0b5', fontSize: 11 } },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: DIMS.map((d) => d.toUpperCase()),
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
          data: DIMS.map((d) => ({
            value: weights[d] ?? 0,
            itemStyle: { color: DIM_COLORS[d] ?? '#6366f1' },
          })),
          barWidth: 20,
        },
        {
          name: '默认',
          type: 'bar',
          data: DIMS.map((d) => ({
            value: defaults[d] ?? 0,
            itemStyle: { color: DIM_COLORS[d] ?? '#6366f1', opacity: 0.4 },
          })),
          barWidth: 20,
        },
      ],
    };
  }, [weights, defaults]);

  const total = useMemo(
    () => Object.values(weights).reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0),
    [weights],
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

            {/* 学习进度统计行 */}
            <div className="grid grid-cols-4 gap-2 mt-3 mb-1">
              <Stat label="更新次数" value={String(data.update_count ?? 0)} />
              <Stat
                label="最后更新"
                value={data.last_update ? fmtDateTime(data.last_update) : '未学习'}
              />
              <Stat label="衰减因子" value={data.decay_factor?.toFixed(2) ?? '0.95'} />
              <Stat label="最小样本" value={String(data.min_outcomes ?? 1)} />
            </div>

            {/* 权重差异 + 后验可信区间 */}
            <div className="grid grid-cols-2 gap-2 mt-2">
              {DIMS.map((d) => {
                const w = weights[d] ?? 0;
                const def = defaults[d] ?? 0;
                const diff = w - def;
                const ci = posterior[d]?.credible_interval_95;
                const pMean = posterior[d]?.posterior_mean;
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
                    {ci && pMean !== undefined && (
                      <div className="mt-1 pt-1 border-t border-[var(--color-border)]/50">
                        <div className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-wider">
                          后验均值 {toWeightPct(pMean as number)}%
                        </div>
                        <div className="text-[9px] text-[var(--color-text-muted)] font-mono">
                          CI95: [
                          {toWeightPct(ci[0])}
                          , {toWeightPct(ci[1])}
                          ]
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-2 text-[10px] text-[var(--color-text-muted)] font-mono flex items-center justify-between">
              <span>weight_delta 总和: 0 (当前=默认基线)</span>
              <span>合计: {total.toFixed(3)}</span>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5">
      <div className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-wider">{label}</div>
      <div className="text-xs font-mono mt-0.5">{value}</div>
    </div>
  );
}

function fmtDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
