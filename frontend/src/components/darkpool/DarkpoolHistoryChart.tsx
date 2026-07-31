/**
 * Darkpool 历史走势 (DIX + Short Ratio + EMA Crossover)
 * - 主轴 DIX
 * - 右轴 Short Ratio
 * - 叠加 EMA fast(5) / EMA slow(20) 区域
 */
import ReactECharts from 'echarts-for-react';
import type { DarkpoolHistoryRow } from '@/lib/api/darkpool';
import { useMemo } from 'react';
import { fmtTime } from '@/lib/utils/format';

interface Props {
  history: DarkpoolHistoryRow[];
  height?: number;
  loading?: boolean;
}

export function DarkpoolHistoryChart({ history, height = 280, loading }: Props) {
  const option = useMemo(() => {
    const series: Array<Record<string, unknown>> = [];
    if (history && history.length > 0) {
      series.push({
        name: 'DIX',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: '#6366f1' },
        areaStyle: { color: 'rgba(99,102,241,0.10)' },
        data: history.map((h) => [new Date(h.date).getTime(), h.dix_value ?? null]),
      });
      series.push({
        name: 'Short Ratio',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        yAxisIndex: 1,
        lineStyle: { width: 1, color: '#ef4444', type: 'dashed' },
        data: history.map((h) => [new Date(h.date).getTime(), h.aggregated_signal ? 1 : 0]),
      });
      const emaFast = history.map((h) => [new Date(h.date).getTime(), h.ema_fast_5 ?? null]);
      const emaSlow = history.map((h) => [new Date(h.date).getTime(), h.ema_slow_20 ?? null]);
      // 仅当 EMA 数据存在才添加
      if (emaFast.some((p) => p[1] != null)) {
        series.push({
          name: 'EMA5',
          type: 'line' as const,
          showSymbol: false,
          yAxisIndex: 1,
          smooth: true,
          lineStyle: { width: 1, color: '#22c55e' },
          data: emaFast,
        });
      }
      if (emaSlow.some((p) => p[1] != null)) {
        series.push({
          name: 'EMA20',
          type: 'line' as const,
          showSymbol: false,
          yAxisIndex: 1,
          smooth: true,
          lineStyle: { width: 1, color: '#f59e0b', type: 'dotted' },
          data: emaSlow,
        });
      }
      series.push({
        name: '聚合信号',
        type: 'scatter' as const,
        symbolSize: (v: number[]) => (Array.isArray(v) && v[1] ? 8 : 4),
        itemStyle: { color: '#ef4444' },
        yAxisIndex: 1,
        data: history.map((h) => [new Date(h.date).getTime(), h.aggregated_signal ? 1 : 0]),
      });
    }

    return {
      legend: { textStyle: { color: '#a0a0b5', fontSize: 10 }, top: 0, right: 8 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17,17,40,0.92)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#f0f0f5', fontSize: 11 },
      },
      grid: { left: 60, right: 60, top: 28, bottom: 24 },
      xAxis: {
        type: 'time' as const,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#6b6b80', fontSize: 10 },
      },
      yAxis: [
        {
          type: 'value' as const,
          name: 'DIX',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
        {
          type: 'value' as const,
          name: 'EMA / Sig',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          position: 'right' as const,
          min: -0.5,
          max: 1.5,
          splitLine: { show: false },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
      ],
      series,
    };
  }, [history]);

  if (loading) {
    return <div className="msr-card h-[280px] bg-[var(--color-bg-elevated)] animate-pulse" aria-busy="true" />;
  }
  if (!history.length) {
    return (
      <div
        className="msr-card flex items-center justify-center text-sm text-[var(--color-text-muted)]"
        style={{ height }}
        role="status"
      >
        暂无 Darkpool 历史数据
      </div>
    );
  }
  return (
    <div className="msr-card" role="figure" aria-label="Darkpool 历史走势">
      <ReactECharts option={option} style={{ height, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 text-center">
        DIX (紫) · EMA5/EMA20 交叉 (右轴) · 聚合信号 (红点)
      </div>
      {history.length > 0 && history[0].date && (
        <div className="text-[10px] text-[var(--color-text-muted)] text-right mt-1">
          最近：<span className="font-mono">{fmtTime(history[0].date + 'T00:00:00')}</span>
        </div>
      )}
    </div>
  );
}
