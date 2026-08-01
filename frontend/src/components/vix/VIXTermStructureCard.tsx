/**
 * VIX Term Structure 可视化
 * - 横向条形：VIX Spot vs VX1 vs VX2
 * - 颜色提示：Contango(绿) / Backwardation(红) / Flat(黄)
 * - 显示 Ratio = vix_spot / vx2
 */
import { Card, CardContent } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import { fmtNum, fmtPct } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';
import { useMemo } from 'react';

interface Props {
  vixSpot: number | null;
  vx1: number | null;
  vx2: number | null;
  state: 'contango' | 'backwardation' | 'flat' | null | string;
  // FIX-35: the backend already returns the canonical term-structure
  // ratio (``vx_3m_proxy / vix_spot - 1`` in the fetcher). Forward it
  // here so the parent stops having to recompute the ratio client-side
  // from raw spot/vx2 — different definitions of "ratio" produced
  // inconsistent percentages between the chart card and history card.
  termStructureRatio?: number | null;
  loading?: boolean;
}

export function VIXTermStructureCard({ vixSpot, vx1, vx2, state, termStructureRatio, loading }: Props) {
  const option = useMemo(() => {
    const labels = ['VX1 (近月)', 'VIX Spot', 'VX2 (远月)'];
    const data = [vx1 ?? null, vixSpot ?? null, vx2 ?? null];
    const colors = ['#10b981', '#6366f1', '#a78bfa'];
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17,17,40,0.92)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#f0f0f5', fontSize: 11 },
      },
      grid: { left: 90, right: 16, top: 16, bottom: 24 },
      xAxis: {
        type: 'value' as const,
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
        axisLabel: { color: '#6b6b80', fontSize: 10 },
      },
      yAxis: {
        type: 'category' as const,
        data: labels,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#a0a0b5', fontSize: 11 },
      },
      series: [
        {
          type: 'bar' as const,
          data: data.map((v, i) => ({
            value: v ?? 0,
            itemStyle: { color: colors[i], borderRadius: 4 },
          })),
          barWidth: '45%',
          label: {
            show: true,
            position: 'right' as const,
            color: '#f0f0f5',
            fontSize: 11,
            formatter: (p: { value: number }) => (p.value == null || p.value === 0 ? '—' : p.value.toFixed(2)),
          },
        },
      ],
    };
  }, [vixSpot, vx1, vx2]);

  // FIX-35: prefer the backend-provided ratio when available (matches the
  // fetcher's ``vx_3m_proxy / vix_spot - 1`` definition). Fall back to the
  // historical VIX/VX2 fallback only when the backend didn't supply it.
  const ratio =
    termStructureRatio != null
      ? 1 + termStructureRatio
      : vixSpot != null && vx2 != null && vx2 > 0
        ? vixSpot / vx2
        : null;
  const contangoPct =
    termStructureRatio != null
      ? termStructureRatio
      : ratio != null
        ? ratio - 1
        : null;

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-28 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="h-[160px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  const stateCls =
    state === 'backwardation'
      ? 'bg-[var(--color-danger)]/10 text-[var(--color-danger)]'
      : state === 'contango'
        ? 'bg-[var(--color-success)]/10 text-[var(--color-success)]'
        : state === 'flat'
          ? 'bg-[var(--color-warning)]/10 text-[var(--color-warning)]'
          : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]';

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">期限结构</h3>
          <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', stateCls)}>
            {state ?? '—'}
          </span>
        </div>
        <ReactECharts option={option} style={{ height: 160, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
        <div className="grid grid-cols-2 gap-2 mt-2">
          <div className="text-[11px] text-[var(--color-text-muted)]">
            VIX/VX2
            <span className="msr-number text-sm font-semibold ml-1.5 text-[var(--color-text-primary)]">
              {fmtNum(ratio, 3)}
            </span>
          </div>
          <div className="text-[11px] text-[var(--color-text-muted)] text-right">
            Contango%
            <span className={cn('msr-number text-sm font-semibold ml-1.5', contangoPct != null && contangoPct > 0 ? 'text-[var(--color-warning)]' : 'text-[var(--color-text-primary)]')}>
              {contangoPct != null ? fmtPct(contangoPct, 2) : '—'}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
