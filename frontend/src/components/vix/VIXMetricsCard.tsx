/**
 * VIX 关键指标卡片（Spot / VX1 / VX2 / Term-structure state / Panic Premium）
 */
import { Card, CardContent } from 'sparkdesign';
import { fmtNum, fmtPct } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface VIXMetrics {
  vix_spot: number | null;
  vx1: number | null;
  vx2: number | null;
  term_structure_ratio: number | null;
  term_structure_state: 'contango' | 'backwardation' | 'flat' | null | string;
  panic_premium: number | null;
  timestamp?: string | null;
}

function stateToneCls(
  s: VIXMetrics['term_structure_state']
): { text: string; bg: string; label: string } {
  if (s === 'backwardation')
    return {
      text: 'text-[var(--color-danger)]',
      bg: 'bg-[var(--color-danger)]/10',
      label: 'Backwardation · 危机',
    };
  if (s === 'contango')
    return {
      text: 'text-[var(--color-success)]',
      bg: 'bg-[var(--color-success)]/10',
      label: 'Contango · 正常',
    };
  if (s === 'flat')
    return {
      text: 'text-[var(--color-warning)]',
      bg: 'bg-[var(--color-warning)]/10',
      label: 'Flat · 转折',
    };
  return {
    text: 'text-[var(--color-text-muted)]',
    bg: 'bg-[var(--color-bg-elevated)]',
    label: '—',
  };
}

function panicTone(v: number | null): { text: string; bg: string; label: string } {
  if (v == null)
    return { text: 'text-[var(--color-text-muted)]', bg: 'bg-[var(--color-bg-elevated)]', label: '—' };
  if (v > 0.4) return { text: 'text-[var(--color-danger)]', bg: 'bg-[var(--color-danger)]/10', label: '高恐慌溢价' };
  if (v > 0.15) return { text: 'text-[var(--color-warning)]', bg: 'bg-[var(--color-warning)]/10', label: '偏高' };
  return { text: 'text-[var(--color-success)]', bg: 'bg-[var(--color-success)]/10', label: '正常' };
}

export function VIXMetricsCard({ latest, loading }: { latest: VIXMetrics | null; loading?: boolean }) {
  const stateTone = stateToneCls(latest?.term_structure_state ?? null);
  const panic = panicTone(latest?.panic_premium ?? null);

  if (loading || !latest) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-24 bg-[var(--color-border)] rounded animate-pulse mb-3" />
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">VIX 关键指标</h3>
          <div className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', stateTone.bg, stateTone.text)}>
            {stateTone.label}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">VIX Spot</div>
            <div className="msr-number text-xl mt-1">{fmtNum(latest.vix_spot, 2)}</div>
          </div>
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">VX1 / VX2</div>
            <div className="msr-number text-xl mt-1">
              {fmtNum(latest.vx1, 2)} <span className="text-[var(--color-text-muted)] text-sm">/ {fmtNum(latest.vx2, 2)}</span>
            </div>
          </div>
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Term Ratio</div>
            <div className="msr-number text-xl mt-1">{fmtNum(latest.term_structure_ratio, 3)}</div>
          </div>
        </div>

        {/* Panic Premium */}
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--color-text-muted)]">波动率风险溢价 (VRP) / 恐慌溢价</span>
            <span className={cn('text-xs font-bold', panic.text)}>{fmtPct(latest.panic_premium ?? null, 2)}</span>
          </div>
          <div
            className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded overflow-hidden"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={1}
            aria-valuenow={Math.min(1, Math.max(0, latest.panic_premium ?? 0))}
            aria-label="恐慌溢价进度"
          >
            <div
              className={cn(
                'h-full transition-all duration-300',
                (latest.panic_premium ?? 0) > 0.4
                  ? 'bg-[var(--color-danger)]'
                  : (latest.panic_premium ?? 0) > 0.15
                    ? 'bg-[var(--color-warning)]'
                    : 'bg-[var(--color-success)]'
              )}
              style={{ width: `${Math.min(100, Math.max(0, (latest.panic_premium ?? 0) * 100))}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className={cn('text-[10px] font-bold uppercase tracking-wider', panic.text)}>{panic.label}</span>
            {latest.timestamp && (
              <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{latest.timestamp}</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
