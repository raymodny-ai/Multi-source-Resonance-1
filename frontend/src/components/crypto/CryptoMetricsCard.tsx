/**
 * Crypto 衍生品关键指标卡片
 * - BTC Funding Rate
 * - BTC OI + 1h 变化
 * - Leverage Ratio (ELR from CryptoQuant)
 * - 异常状态标签（liquidation_spike / funding_anomaly / oi_crash / leverage_cleanup）
 */
import { Card, CardContent } from 'sparkdesign';
import { fmtNum, fmtPct, fmtTime } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';
import type { CryptoLatest } from '@/lib/api/crypto';

interface Props {
  latest: CryptoLatest | null;
  loading?: boolean;
}

function fundingTone(rate: number | null): {
  text: string;
  bg: string;
  label: string;
} {
  if (rate == null) return { text: 'text-[var(--color-text-muted)]', bg: 'bg-[var(--color-bg-elevated)]', label: '—' };
  if (rate > 0.0005) return { text: 'text-[var(--color-danger)]', bg: 'bg-[var(--color-danger)]/10', label: '多头过热' };
  if (rate < -0.0005) return { text: 'text-[var(--color-success)]', bg: 'bg-[var(--color-success)]/10', label: '空头过热' };
  return { text: 'text-[var(--color-info)]', bg: 'bg-[var(--color-info)]/10', label: '中性' };
}

export function CryptoMetricsCard({ latest, loading }: Props) {
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

  const funding = latest.btc_funding_rate ?? null;
  const ft = fundingTone(funding);
  const oi = latest.btc_oi ?? null;
  const oiChange1h = latest.oi_change_1h ?? null;
  const elr = latest.cryptoquant_elr ?? null;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">BTC 衍生品</h3>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{fmtTime(latest.timestamp)}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Funding Rate */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Funding Rate</div>
            <div className="msr-number text-lg mt-1">{fmtPct(funding, 4)}</div>
            <span className={cn('inline-block text-[10px] mt-1 px-1.5 py-0.5 rounded uppercase tracking-wider font-bold', ft.bg, ft.text)}>
              {ft.label}
            </span>
          </div>

          {/* Open Interest */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">BTC OI</div>
            <div className="msr-number text-lg mt-1">{oi != null ? Math.round(oi).toLocaleString('en-US') : '—'}</div>
            {oiChange1h != null && (
              <div
                className={cn(
                  'text-[10px] font-mono mt-1',
                  oiChange1h > 0 ? 'text-[var(--color-success)]' : oiChange1h < 0 ? 'text-[var(--color-danger)]' : 'text-[var(--color-text-muted)]',
                )}
              >
                1h {oiChange1h > 0 ? '+' : ''}
                {fmtPct(oiChange1h, 2)}
              </div>
            )}
          </div>

          {/* ELR (Estimated Leverage Ratio) */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">ELR</div>
            <div className="msr-number text-lg mt-1">{fmtNum(elr, 2)}</div>
            <span className="text-[10px] text-[var(--color-text-muted)] mt-1 inline-block">
              估计杠杆倍数
            </span>
          </div>

          {/* OI Change 1h */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">OI Δ 1h</div>
            <div
              className={cn(
                'msr-number text-lg mt-1',
                (oiChange1h ?? 0) > 0 ? 'text-[var(--color-success)]' : (oiChange1h ?? 0) < 0 ? 'text-[var(--color-danger)]' : '',
              )}
            >
              {oiChange1h == null ? '—' : `${oiChange1h > 0 ? '+' : ''}${(oiChange1h * 100).toFixed(2)}%`}
            </div>
          </div>
        </div>

        {/* Boolean flags */}
        <div className="flex flex-wrap gap-2 mt-3">
          <BoolFlag label="爆仓激增" value={latest.liquidation_spike} />
          <BoolFlag label="资金费率异常" value={latest.funding_anomaly} />
          <BoolFlag label="OI 闪崩" value={latest.oi_crash} />
          <BoolFlag label="杠杆清理" value={latest.leverage_cleanup} />
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
          ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)] border-[var(--color-danger)]/40'
          : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border-[var(--color-border)]',
      )}
      title={label}
    >
      <span
        className={cn(
          'inline-block w-1.5 h-1.5 rounded-full',
          value ? 'bg-[var(--color-danger)] animate-pulse-dot' : 'bg-[var(--color-text-muted)]',
        )}
        aria-hidden
      />
      {label}
    </span>
  );
}
