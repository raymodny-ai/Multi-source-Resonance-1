/**
 * Dark Pool 关键指标卡片
 * - DIX (Dark pool Index)
 * - Short Ratio
 * - 20d / 60d 斜率
 * - 信号：聚合信号 / 零交叉 / 动量反转
 */
import { Card, CardContent } from 'sparkdesign';
import { fmtNum, fmtTime } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';
import type { DarkpoolLatest } from '@/lib/api/darkpool';

interface Props {
  latest: DarkpoolLatest | null;
  loading?: boolean;
}

function signalTone(value: string | null | undefined): { bg: string; text: string; label: string } {
  if (value == null || value === '') return { bg: 'bg-[var(--color-bg-elevated)]', text: 'text-[var(--color-text-muted)]', label: '—' };
  const v = String(value).toLowerCase();
  if (v === 'buy' || v === 'long' || v === 'bullish') {
    return { bg: 'bg-[var(--color-success)]/10', text: 'text-[var(--color-success)]', label: '买入' };
  }
  if (v === 'sell' || v === 'short' || v === 'bearish') {
    return { bg: 'bg-[var(--color-danger)]/10', text: 'text-[var(--color-danger)]', label: '卖出' };
  }
  if (v === 'neutral' || v === 'flat') {
    return { bg: 'bg-[var(--color-info)]/10', text: 'text-[var(--color-info)]', label: '中性' };
  }
  // 0 / 1 / 具体文本
  if (v === '0') return { bg: 'bg-[var(--color-bg-elevated)]', text: 'text-[var(--color-text-muted)]', label: '无' };
  if (v === '1') return { bg: 'bg-[var(--color-warning)]/10', text: 'text-[var(--color-warning)]', label: '触发' };
  return { bg: 'bg-[var(--color-bg-elevated)]', text: 'text-[var(--color-text-muted)]', label: v };
}

export function DarkpoolMetricsCard({ latest, loading }: Props) {
  if (loading || !latest) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-32 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const dixTone = (() => {
    const v = latest.dix_value;
    if (v == null) return 'text-[var(--color-text-muted)]';
    if (v > 0.6) return 'text-[var(--color-warning)]';
    if (v < 0.4) return 'text-[var(--color-success)]';
    return 'text-[var(--color-info)]';
  })();

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">暗池指标</h3>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{fmtTime(latest.date)}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">DIX</div>
            <div className={cn('msr-number text-lg mt-1', dixTone)}>{fmtNum(latest.dix_value, 3)}</div>
            <span className="text-[10px] text-[var(--color-text-muted)] mt-1 inline-block">
              暗池占比
            </span>
          </div>

          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Short Ratio</div>
            <div className="msr-number text-lg mt-1">{fmtNum(latest.chartexchange_short_ratio, 2)}</div>
            <span className="text-[10px] text-[var(--color-text-muted)] mt-1 inline-block">
              回补天数 (Short Ratio)
            </span>
          </div>

          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Slope 20d / 60d</div>
            <div className="msr-number text-lg mt-1">
              {fmtNum(latest.stockgrid_20d_slope, 3)} <span className="text-[var(--color-text-muted)] text-sm">/ {fmtNum(latest.stockgrid_60d_slope, 3)}</span>
            </div>
            <span className="text-[10px] text-[var(--color-text-muted)] mt-1 inline-block">
              短期/中期斜率
            </span>
          </div>

          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">V_NET</div>
            <div className="msr-number text-lg mt-1">{fmtNum(latest.v_net, 2)}</div>
            <span className="text-[10px] text-[var(--color-text-muted)] mt-1 inline-block">
              净流量
            </span>
          </div>
        </div>

        {/* Signal flags */}
        <div className="flex flex-wrap gap-2 mt-3">
          <BoolFlag label="聚合信号" value={latest.aggregated_signal} />
          <BoolFlag label="DBMF MA5 恢复" value={latest.dbmf_ma5_recovery} />
          <BoolFlag label="Stockgrid 背离" value={latest.stockgrid_divergence} />
          {latest.zero_cross_signal && (
            <SignalPill label="零交叉" value={latest.zero_cross_signal} />
          )}
          {latest.momentum_reversal_signal && (
            <SignalPill label="动量反转" value={latest.momentum_reversal_signal} />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function BoolFlag({ label, value }: { label: string; value: boolean | null | undefined }) {
  if (value == null) return null;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider',
        value
          ? 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border-[var(--color-warning)]/40'
          : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border-[var(--color-border)]',
      )}
    >
      <span
        className={cn(
          'inline-block w-1.5 h-1.5 rounded-full',
          value ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-text-muted)]',
        )}
        aria-hidden
      />
      {label}
    </span>
  );
}

function SignalPill({ label, value }: { label: string; value: string | null | undefined }) {
  const tone = signalTone(value);
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', tone.bg, tone.text)}>
      {label}: {tone.label}
    </span>
  );
}
