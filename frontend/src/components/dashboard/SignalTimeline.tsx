/**
 * 24h 信号时间线（sparkline + 等级点）
 * - 折线表示综合分数（最近 24h 历史的最近 24 个 cycle）
 * - 颜色点表示各级信号
 */
import ReactECharts from 'echarts-for-react';
import { useSignalsHistory, defaultSignalFilters } from '@/lib/hooks/useSignals';
import { fmtClock, levelTone } from '@/lib/utils/format';
import { levelOf, scoreOf, tsOf } from '@/lib/utils/signal';

function toneColor(level: number): string {
  const t = levelTone(level);
  if (t === 'danger') return '#ef4444';
  if (t === 'warning') return '#f59e0b';
  return '#3b82f6';
}

export function SignalTimeline({ height = 120 }: { height?: number }) {
  const { data, isLoading } = useSignalsHistory({
    ...defaultSignalFilters,
    limit: 24,
    page: 1,
  });
  const rows = (data?.data ?? []).slice().reverse(); // 按时间正序

  const option = {
    grid: { left: 30, right: 12, top: 8, bottom: 18 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17,17,40,0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#f0f0f5' },
      formatter: (params: { axisValue: string; data: { score: number | null; level: number } }[]) => {
        const p = params[0];
        return `${p.axisValue}<br/>分数 ${p.data.score?.toFixed(2) ?? '—'}<br/>等级 ${p.data.level}`;
      },
    },
    xAxis: {
      type: 'category',
      data: rows.map((s) => fmtClock(tsOf(s), '')),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#6b6b80', fontSize: 10, interval: 3 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 5,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#6b6b80', fontSize: 10 },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#6366f1', width: 1.5 },
        itemStyle: {
          color: (p: { data: { level: number } }) => toneColor(p.data.level),
          borderColor: '#6366f1',
        },
        data: rows.map((s) => ({ value: scoreOf(s), score: scoreOf(s), level: levelOf(s) })),
      },
    ],
  };

  return (
    <div className="msr-card flex flex-col" role="figure" aria-label="最近 24 小时信号时间线">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">信号时间线 · 最近 24h</h3>
        <span className="text-[10px] text-[var(--color-text-muted)]">{rows.length} 条</span>
      </div>
      {isLoading && rows.length === 0 ? (
        <div className="h-[120px] w-full bg-[var(--color-border)] rounded animate-pulse" />
      ) : rows.length === 0 ? (
        <div className="h-[120px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
          暂无信号
        </div>
      ) : (
        <ReactECharts
          option={option}
          style={{ height, width: '100%' }}
          notMerge
          lazyUpdate
          opts={{ renderer: 'canvas' }}
        />
      )}
    </div>
  );
}
