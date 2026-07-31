/**
 * Crypto 历史走势 (Funding Rate + OI dual-axis)
 */
import ReactECharts from 'echarts-for-react';
import type { CryptoHistoryRow } from '@/lib/api/crypto';
import { useMemo } from 'react';
import { fmtTime } from '@/lib/utils/format';

interface Props {
  history: CryptoHistoryRow[];
  height?: number;
  loading?: boolean;
}

export function CryptoHistoryChart({ history, height = 280, loading }: Props) {
  const option = useMemo(() => {
    const series: Array<Record<string, unknown>> = [];
    if (history && history.length > 0) {
      series.push({
        name: 'Funding Rate',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        yAxisIndex: 0,
        lineStyle: { width: 1.5, color: '#6366f1' },
        areaStyle: { color: 'rgba(99,102,241,0.10)' },
        data: history.map((h) => [
          new Date(h.timestamp).getTime(),
          typeof h.btc_funding_rate === 'number' ? h.btc_funding_rate * 100 : null,
        ]),
        markLine: {
          symbol: 'none',
          data: [{ yAxis: 0, lineStyle: { color: 'rgba(255,255,255,0.2)', type: 'dashed' } }],
        },
      });
      series.push({
        name: 'BTC OI',
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        yAxisIndex: 1,
        lineStyle: { width: 1, color: '#f59e0b' },
        data: history.map((h) => [new Date(h.timestamp).getTime(), h.btc_oi ?? null]),
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
          name: 'Funding (%)',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
          axisLabel: { color: '#6b6b80', fontSize: 10 },
        },
        {
          type: 'value' as const,
          name: 'OI',
          nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
          position: 'right' as const,
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
        暂无 Crypto 历史数据
      </div>
    );
  }
  return (
    <div className="msr-card" role="figure" aria-label="Crypto 衍生品历史">
      <ReactECharts option={option} style={{ height, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 text-center">
        Funding Rate × 100 (紫) · BTC OI (橙, 右轴)
      </div>
      {history.length > 0 && history[0].timestamp && (
        <div className="text-[10px] text-[var(--color-text-muted)] text-right mt-1">
          最近：<span className="font-mono">{fmtTime(history[0].timestamp)}</span>
        </div>
      )}
    </div>
  );
}
