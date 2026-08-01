/**
 * GEX 单符号 strikes 分布图
 * - 双柱图：Call GEX / Put GEX（正值双向发散）
 * - 当前 Spot 用虚线标识
 * - Call Wall / Put Wall 用 MarkPoint 标注
 */
import ReactECharts from 'echarts-for-react';
import type { GEXStrikeRow } from '@/lib/api/types';
import { Card, CardContent } from 'sparkdesign';
import { fmtNum } from '@/lib/utils/format';
import { useMemo } from 'react';

interface Props {
  strikes: GEXStrikeRow[];
  spot: number | null;
  callWall: number | null;
  putWall: number | null;
  height?: number;
  loading?: boolean;
}

export function GEXStrikesChart({ strikes, spot, callWall, putWall, height = 320, loading }: Props) {
  const option = useMemo(() => {
    const sorted = [...(strikes ?? [])].sort((a, b) => a.strike - b.strike);
    const labels = sorted.map((s) => s.strike);
    // FIX-50: normalise null ↦ null for BOTH call and put (the previous
    // version coerced call_gex nulls to ``0`` but kept put_gex as ``null``,
    // so a row where one side had no data drew a zero-height call bar
    // and a gap in the put bar — visually misleading). Now both sides
    // get ``null`` and echarts renders a gap for missing data.
    const callData = sorted.map((s) =>
      typeof s.call_gex === 'number' ? s.call_gex : null,
    );
    const putData = sorted.map((s) =>
      typeof s.put_gex === 'number' ? -Math.abs(s.put_gex) : null,
    );

    const markPoints: Array<Record<string, unknown>> = [];
    if (spot != null) {
      markPoints.push({
        name: 'Spot',
        coord: [spot, 0],
        symbol: 'pin',
        symbolSize: 26,
        itemStyle: { color: '#10b981' },
        label: {
          color: '#10b981',
          fontSize: 10,
          position: 'top' as const,
          offset: [0, 4],
          formatter: 'Spot',
        },
      });
    }
    if (callWall != null) {
      // FIX-41: the x-axis is 'category', so the markPoint coord must
      // be the category index, not the raw strike value. The previous
      // ``coord: [callWall, y]`` placed the marker somewhere off-axis
      // whenever the strike was slightly off-grid (e.g. 582.5 vs 582).
      const x = labels.indexOf(callWall);
      const y = x >= 0 ? callData[x] : null;
      markPoints.push({
        name: 'CallWall',
        coord: [x >= 0 ? x : callWall, y],
        symbol: 'triangle',
        symbolSize: 12,
        itemStyle: { color: '#22c55e' },
        label: {
          color: '#22c55e',
          fontSize: 10,
          formatter: 'Call Wall',
          position: 'top' as const,
        },
      });
    }
    if (putWall != null) {
      // FIX-41: same correction for the put wall.
      const x = labels.indexOf(putWall);
      const y = x >= 0 ? putData[x] : null;
      markPoints.push({
        name: 'PutWall',
        coord: [x >= 0 ? x : putWall, y],
        symbol: 'triangle',
        symbolRotate: 180,
        symbolSize: 12,
        itemStyle: { color: '#f97316' },
        label: {
          color: '#f97316',
          fontSize: 10,
          formatter: 'Put Wall',
          position: 'bottom' as const,
        },
      });
    }

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(17,17,40,0.92)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#f0f0f5', fontSize: 11 },
        formatter: (params: unknown) => {
          const list = Array.isArray(params) ? (params as Array<{ axisValue: number; seriesName: string; value: number; dataIndex: number }>) : [];
          if (list.length === 0) return '';
          const idx = list[0].dataIndex;
          const row = sorted[idx];
          if (!row) return '';
          const net = typeof row.net_gex === 'number' ? row.net_gex : 0;
          return `
            <div style="font-weight:600">Strike ${row.strike}</div>
            <div>Call OI: ${row.call_oi?.toLocaleString() ?? '—'}</div>
            <div>Put OI: ${row.put_oi?.toLocaleString() ?? '—'}</div>
            <div>Call GEX: ${(row.call_gex ?? 0).toFixed(2)}</div>
            <div>Put GEX: ${(row.put_gex ?? 0).toFixed(2)}</div>
            <div style="margin-top:4px">Net GEX: <b>${net.toFixed(2)}</b></div>
          `;
        },
      },
      legend: {
        textStyle: { color: '#a0a0b5', fontSize: 10 },
        top: 4,
        right: 8,
      },
      grid: { left: 60, right: 16, top: 28, bottom: 32 },
      xAxis: {
        type: 'category' as const,
        data: labels,
        name: 'Strike',
        nameLocation: 'middle' as const,
        nameGap: 22,
        nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: {
          color: '#6b6b80',
          fontSize: 10,
          interval: Math.max(1, Math.floor(labels.length / 12)),
        },
      },
      yAxis: {
        type: 'value' as const,
        name: 'GEX (|Call| / |Put|)',
        nameTextStyle: { color: '#a0a0b5', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
        axisLabel: { color: '#6b6b80', fontSize: 10 },
      },
      series: [
        {
          name: 'Call GEX',
          type: 'bar' as const,
          stack: 'gex',
          data: callData,
          itemStyle: { color: '#22c55e' },
          barWidth: '60%',
        },
        {
          name: 'Put GEX',
          type: 'bar' as const,
          stack: 'gex',
          data: putData,
          itemStyle: { color: '#ef4444' },
          barWidth: '60%',
          markPoint: { data: markPoints },
        },
      ],
    };
  }, [strikes, spot, callWall, putWall]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-32 bg-[var(--color-border)] rounded mb-3 animate-pulse" />
          <div className="h-[320px] w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }
  if (!strikes || strikes.length === 0) {
    return (
      <Card>
        <CardContent className="p-4 flex items-center justify-center text-sm text-[var(--color-text-muted)]" style={{ height: 320 }} role="status">
          暂无 Strike 分布数据
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-4">
        <h3 className="text-sm font-semibold mb-2">Strike 分布 · {strikes.length} 行权价</h3>
        <ReactECharts option={option} style={{ height, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
        <div className="text-[10px] text-[var(--color-text-muted)] mt-2 flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-[#22c55e]" /> Call GEX ↑
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-[#ef4444]" /> Put GEX ↓
          </span>
          {spot != null && (
            <span className="flex items-center gap-1">
              <span className="inline-block w-1 h-2 bg-[#10b981]" /> Spot <span className="font-mono ml-1">{fmtNum(spot, 2)}</span>
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
