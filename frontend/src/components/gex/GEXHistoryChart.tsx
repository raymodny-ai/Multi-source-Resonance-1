/**
 * GEX 历史走势 (Net GEX + Spot + Call Wall / Put Wall overlay)
 * - 短窗口使用 GEXDashboardView.history
 * - 长窗口使用 GEXDashboardView.long_history（叠加 alpha_factor）
 */
import ReactECharts from 'echarts-for-react';
import type { GEXDashboardView } from '@/lib/api/types';
import { fmtClock } from '@/lib/utils/format';
import { useMemo } from 'react';

interface Props {
  history: GEXDashboardView['history'];
  longHistory?: GEXDashboardView['long_history'];
  height?: number;
  loading?: boolean;
}

export function GEXHistoryChart({ history, longHistory, height = 240, loading }: Props) {
  const option = useMemo(() => {
    const series: Array<Record<string, unknown>> = [];
    if (history && history.length > 0) {
      series.push({
        name: 'Net GEX',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: '#6366f1' },
        areaStyle: { color: 'rgba(99,102,241,0.10)' },
        data: history.map((h) => [
          new Date(h.timestamp).getTime(),
          h.net_gex ?? null,
        ]),
      });
      const spotSeries = history
        .map((h) => [new Date(h.timestamp).getTime(), h.spot_price ?? null] as [number, number | null])
        .filter((p): p is [number, number] => p[1] != null);
      if (spotSeries.length > 0) {
        series.push({
          name: 'Spot',
          type: 'line' as const,
          showSymbol: false,
          yAxisIndex: 1,
          lineStyle: { width: 1, color: '#10b981', type: 'dashed' },
          data: spotSeries,
        });
      }
    }
    if (longHistory && longHistory.length > 0) {
      series.push({
        name: 'GEX (long)',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        yAxisIndex: 0,
        lineStyle: { width: 1, color: '#a78bfa', type: 'dotted' },
        data: longHistory.map((h) => [new Date(h.timestamp).getTime(), h.gex ?? h.gex_calibrated ?? null]),
      });
    }

    return {
      legend: {
        textStyle: { color: '#a0a0b5', fontSize: 10 },
        top: 0,
        right: 8,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17,17,40,0.9)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#f0f0f5', fontSize: 11 },
        formatter: (params: Array<{ axisValue: number; marker: string; seriesName: string; value: [number, number] }>) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const head = new Date(params[0].axisValue).toLocaleString('zh-CN');
          const rows = params
            .map((p) => {
              const v = Array.isArray(p.value) ? p.value[1] : null;
              return `${p.marker}${p.seriesName}: ${v == null ? '—' : v.toFixed(2)}`;
            })
            .join('<br/>');
          return `${head}<br/>${rows}`;
        },
      },
      grid: { left: 60, right: 60, top: 28, bottom: 24 },
      xAxis: {
        type: 'time' as const,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#6b6b80', fontSize: 10 },
      },
      yAxis: [
        {
          type: 'value' as const,
          name: 'Net GEX',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
          axisLabel: { color: '#6b6b80', fontSize: 10, formatter: (v: number) => v.toFixed(1) },
        },
        {
          type: 'value' as const,
          name: 'Spot',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          position: 'right' as const,
          splitLine: { show: false },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
      ],
      series,
    };
  }, [history, longHistory]);

  if (loading) {
    return <div className="msr-card h-[240px] bg-[var(--color-bg-elevated)] animate-pulse" aria-busy="true" />;
  }
  return (
    <div className="msr-card" role="figure" aria-label="GEX 历史走势">
      <ReactECharts option={option} style={{ height, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 text-center">
        短窗口 GEX (实线 · 紫色面积) · Spot (绿虚线，右轴) · 长窗口 GEX (紫点线)
      </div>
    </div>
  );
}

/** 纯线条占位（用作 loading + 错误态） */
export function GEXHistoryChartSkeleton({ height = 240 }: { height?: number }) {
  return (
    <div
      className="msr-card bg-[var(--color-bg-elevated)] animate-pulse"
      style={{ height }}
      aria-busy="true"
      aria-label="加载 GEX 历史走势"
    >
      <div className="h-3 w-24 bg-[var(--color-border)] rounded mb-2 ml-2 mt-2" />
      <div className="h-[180px] m-2 bg-[var(--color-bg-base)] rounded" />
    </div>
  );
}

export function GEXHistoryChartEmpty({ hint }: { hint?: string }) {
  return (
    <div className="msr-card flex items-center justify-center text-sm text-[var(--color-text-muted)]" style={{ height: 240 }} role="status">
      {hint ?? '暂无 GEX 历史数据'}
    </div>
  );
}

export function fmtRowsTs(ts: string) {
  return fmtClock(ts, '—');
}
