/**
 * 信号详情 Drawer
 * - 4 维度雷达图（RadarChart）
 * - 时间戳 + 4 维度分项 + Outcome + details JSON
 * - 底部「确认」按钮（已确认则隐藏）
 */
import { useMemo } from 'react';
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from 'sparkdesign';
import { Badge } from 'sparkdesign';
import { Button } from 'sparkdesign';
import { Separator } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import type { Signal } from '@/lib/api/types';
import { fmtClock, fmtNum, fmtPct, fmtTime, levelTone } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface SignalDetailDrawerProps {
  signal: Signal | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAcknowledge: (signal: Signal) => void;
  acknowledging?: boolean;
}

function dimensionValue(s: Signal, key: keyof Signal): number {
  const v = s[key];
  return typeof v === 'number' && !Number.isNaN(v) ? v : 0;
}

export function SignalDetailDrawer({
  signal,
  open,
  onOpenChange,
  onAcknowledge,
  acknowledging = false,
}: SignalDetailDrawerProps) {
  const radarOption = useMemo(() => {
    if (!signal) return {};
    return {
      tooltip: {},
      radar: {
        indicator: [
          { name: 'GEX', max: 5 },
          { name: 'VIX', max: 5 },
          { name: 'Crypto', max: 5 },
          { name: 'Dark Pool', max: 5 },
        ],
        radius: '60%',
        axisName: { color: '#9ca3af', fontSize: 11 },
        splitArea: { areaStyle: { color: ['rgba(99,102,241,0.04)', 'rgba(99,102,241,0.02)'] } },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: '#6366f1', width: 2 },
          areaStyle: { color: 'rgba(99,102,241,0.18)' },
          itemStyle: { color: '#6366f1' },
          data: [
            {
              value: [
                dimensionValue(signal, 'gex_score'),
                dimensionValue(signal, 'vix_score'),
                dimensionValue(signal, 'crypto_score'),
                dimensionValue(signal, 'darkpool_score'),
              ],
              name: '维度分项',
            },
          ],
        },
      ],
    };
  }, [signal]);

  if (!signal) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent side="right" className="max-w-md">
          <DrawerHeader>
            <DrawerTitle>信号详情</DrawerTitle>
            <DrawerDescription>选择一个信号查看详情</DrawerDescription>
          </DrawerHeader>
        </DrawerContent>
      </Drawer>
    );
  }

  const tone = levelTone(signal.alert_level ?? 0);
  const outcome = signal.outcome;
  const toneCls =
    tone === 'danger'
      ? 'text-[var(--color-danger)]'
      : tone === 'warning'
        ? 'text-[var(--color-warning)]'
        : 'text-[var(--color-info)]';

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent side="right" className="w-full sm:max-w-lg flex flex-col">
        <DrawerHeader>
          <div className="flex items-center justify-between gap-3">
            <DrawerTitle>信号 #{signal.id}</DrawerTitle>
            <span className={cn('font-bold text-sm uppercase tracking-wider', toneCls)}>
              {signal.alert_level != null ? `LEVEL ${signal.alert_level}` : '—'}
            </span>
          </div>
          <DrawerDescription>{fmtTime(signal.timestamp)} · {fmtClock(signal.timestamp)}</DrawerDescription>
        </DrawerHeader>

        <div className="flex-1 overflow-y-auto px-6 py-2 space-y-5">
          {/* Radar */}
          <section>
            <h4 className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">维度雷达</h4>
            <div className="msr-card p-2">
              <ReactECharts
                option={radarOption}
                style={{ height: 260, width: '100%' }}
                notMerge
                opts={{ renderer: 'canvas' }}
              />
            </div>
          </section>

          <Separator />

          {/* Scores */}
          <section>
            <h4 className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">分项明细</h4>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-[var(--color-text-muted)]">综合分</dt>
                <dd className="font-mono font-semibold">{fmtNum(signal.resonance_score, 2)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--color-text-muted)]">GEX</dt>
                <dd className="font-mono">{fmtNum(signal.gex_score, 2)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--color-text-muted)]">VIX</dt>
                <dd className="font-mono">{fmtNum(signal.vix_score, 2)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--color-text-muted)]">Crypto</dt>
                <dd className="font-mono">{fmtNum(signal.crypto_score, 2)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--color-text-muted)]">Dark Pool</dt>
                <dd className="font-mono">{fmtNum(signal.darkpool_score, 2)}</dd>
              </div>
            </dl>
          </section>

          <Separator />

          {/* Outcome */}
          <section>
            <h4 className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">结果评估</h4>
            {!outcome ? (
              <p className="text-sm text-[var(--color-text-muted)]">尚未评估</p>
            ) : (
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      outcome.result === 1
                        ? 'default'
                        : outcome.result === -1
                          ? 'destructive'
                          : 'secondary'
                    }
                  >
                    {outcome.result === 1 ? '盈利' : outcome.result === 0 ? '持平' : outcome.result === -1 ? '亏损' : '待评估'}
                  </Badge>
                  {outcome.forward_return != null && (
                    <span
                      className={cn(
                        'font-mono font-semibold',
                        outcome.forward_return > 0
                          ? 'text-[var(--color-success)]'
                          : outcome.forward_return < 0
                            ? 'text-[var(--color-danger)]'
                            : '',
                      )}
                    >
                      {fmtPct(outcome.forward_return, 2)}
                    </span>
                  )}
                </div>
                {outcome.evaluated_at && (
                  <p className="text-[10px] text-[var(--color-text-muted)]">
                    评估于 {fmtTime(outcome.evaluated_at)}
                  </p>
                )}
              </div>
            )}
          </section>

          <Separator />

          {/* Acknowledgement */}
          <section>
            <h4 className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">确认状态</h4>
            {signal.acknowledged ? (
              <div className="text-sm space-y-0.5">
                <Badge variant="secondary">已确认</Badge>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
                  {signal.acknowledged_by ?? '—'} · {signal.acknowledged_at ? fmtTime(signal.acknowledged_at) : '—'}
                </p>
              </div>
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">未确认</p>
            )}
          </section>

          {/* details JSON */}
          {signal.details && Object.keys(signal.details).length > 0 && (
            <>
              <Separator />
              <section>
                <h4 className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">原始数据</h4>
                <pre className="msr-card p-3 text-[11px] font-mono overflow-x-auto max-h-60 text-[var(--color-text-secondary)]">
                  {JSON.stringify(signal.details, null, 2)}
                </pre>
              </section>
            </>
          )}
        </div>

        <DrawerFooter>
          <div className="flex items-center gap-2">
            {!signal.acknowledged && (
              <Button
                variant="primary"
                onClick={() => onAcknowledge(signal)}
                loading={acknowledging}
                aria-label="确认信号"
              >
                确认信号
              </Button>
            )}
            <DrawerClose asChild>
              <Button variant="outline">关闭</Button>
            </DrawerClose>
          </div>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
