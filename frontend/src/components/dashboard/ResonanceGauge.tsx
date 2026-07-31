/**
 * 共振分数 Gauge（径向，0..5.0）
 * - ECharts gauge 实现
 * - 数值带单位 / 颜色随级别变化 / 骨架态
 */
import ReactECharts from 'echarts-for-react';
import { memo } from 'react';
import { cn } from '@/lib/utils/cn';

export interface ResonanceGaugeProps {
  score: number | null;
  alertLevel: number | null;
  loading?: boolean;
  height?: number;
  className?: string;
}

function levelColor(level: number | null): string {
  if (level == null || level === 0) return '#10b981'; // success
  if (level === 1) return '#3b82f6'; // info
  if (level === 2) return '#f59e0b'; // warning
  return '#ef4444'; // danger
}

function ResonanceGaugeImpl({ score, alertLevel, loading, height = 240, className }: ResonanceGaugeProps) {
  const value = score ?? 0;
  const max = 5.0;
  const color = levelColor(alertLevel);

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max,
        progress: { show: true, width: 18, roundCap: true },
        axisLine: {
          lineStyle: { width: 18, color: [[1, 'rgba(255,255,255,0.08)']] },
        },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        title: { show: false },
        detail: {
          valueAnimation: true,
          fontSize: 36,
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontWeight: 700,
          color: color,
          offsetCenter: [0, '0%'],
          formatter: () => (score == null ? '—' : score.toFixed(2)),
        },
        data: [{ value, itemStyle: { color } }],
      },
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max,
        progress: { show: false },
        axisLine: { show: false },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: 12,
          color: 'rgba(255,255,255,0.4)',
          fontSize: 10,
          formatter: (v: number) => v.toFixed(1),
        },
        anchor: { show: false },
        title: { show: false },
        detail: { show: false },
        data: [{ value: max }],
      },
    ],
  };

  if (loading) {
    return (
      <div
        className={cn('flex items-center justify-center msr-card', className)}
        style={{ height }}
        aria-busy="true"
        aria-label="加载综合共振分数"
      >
        <div className="h-32 w-32 rounded-full border-4 border-[var(--color-border)] border-t-[var(--color-primary)] animate-spin" />
      </div>
    );
  }

  return (
    <div
      className={cn('msr-card flex flex-col', className)}
      role="figure"
      aria-label={`综合共振分数 ${score == null ? '暂无数据' : `${score.toFixed(2)} 分（满分 5.0），警报等级 ${alertLevel ?? 0}`}`}
    >
      <ReactECharts
        option={option}
        style={{ height, width: '100%' }}
        notMerge
        lazyUpdate
        opts={{ renderer: 'canvas' }}
      />
      <div className="text-xs text-[var(--color-text-muted)] text-center -mt-4">综合共振分数 · 共振区间 0–5.0</div>
    </div>
  );
}

export const ResonanceGauge = memo(ResonanceGaugeImpl);