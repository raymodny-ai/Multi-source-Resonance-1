/**
 * VIX 历史走势 (VIX Spot + Term Structure ratio overlay)
 */
import ReactECharts from 'echarts-for-react';
import type { VIXRow, VIXTermStructureHistoryRow } from '@/lib/api/types';
import { useMemo } from 'react';
import { fmtTime } from '@/lib/utils/format';

interface Props {
  history: VIXRow[];
  /** 可选：覆盖 term structure 历史（不同时间尺度） */
  termHistory?: VIXTermStructureHistoryRow[];
  height?: number;
  loading?: boolean;
}

export function VIXHistoryChart({ history, termHistory, height = 260, loading }: Props) {
  const option = useMemo(() => {
    const series: Array<Record<string, unknown>> = [];
    if (history && history.length > 0) {
      series.push({
        name: 'VIX Spot',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: '#6366f1' },
        areaStyle: { color: 'rgba(99,102,241,0.10)' },
        data: history.map((h) => [new Date(h.timestamp).getTime(), h.vix_spot ?? null]),
      });
    }
    if (termHistory && termHistory.length > 0) {
      series.push({
        name: 'Term Ratio',
        type: 'line' as const,
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#f59e0b', type: 'dashed' },
        data: termHistory.map((h) => [
          new Date(h.date).getTime(),
          h.term_structure_ratio ?? null,
        ]),
      });
      series.push({
        name: 'Panic Premium',
        type: 'line' as const,
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#ef4444', type: 'dotted' },
        data: termHistory.map((h) => [new Date(h.date).getTime(), h.panic_premium ?? null]),
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
          name: 'VIX',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
        {
          type: 'value' as const,
          name: 'Ratio',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          position: 'right' as const,
          splitLine: { show: false },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
      ],
      series,
    };
  }, [history, termHistory]);

  if (loading) {
    return <div className="msr-card h-[260px] bg-[var(--color-bg-elevated)] animate-pulse" aria-busy="true" />;
  }
  if (!history.length && !termHistory?.length) {
    return (
      <div
        className="msr-card flex items-center justify-center text-sm text-[var(--color-text-muted)]"
        style={{ height: 260 }}
        role="status"
      >
        暂无 VIX 历史数据
      </div>
    );
  }
  return (
    <div className="msr-card" role="figure" aria-label="VIX 历史走势">
      <ReactECharts option={option} style={{ height, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 text-center">
        VIX Spot (紫面积) · Term Ratio (橙虚) · Panic Premium (红点)
      </div>
      {history.length > 0 && history[0].timestamp && (
        <div className="text-[10px] text-[var(--color-text-muted)] text-right mt-1">
          上次拉取：<span className="font-mono">{fmtTime(history[0].timestamp)}</span>
        </div>
      )}
    </div>
  );
}
