/**
 * Dashboard 4 维度评分卡片（GEX / VIX / Crypto / Darkpool）
 */
import type { DimensionScore } from '@/lib/api/types';
import { fmtNum } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface DimensionDef {
  key: string;
  label: string;
  icon: string;
  description: string;
}

const DIMENSIONS: DimensionDef[] = [
  { key: 'gex', label: 'GEX', icon: 'Γ', description: '期权伽马暴露' },
  { key: 'vix', label: 'VIX', icon: 'σ', description: '波动率期限结构' },
  { key: 'crypto', label: 'Crypto', icon: '₿', description: '加密衍生品' },
  { key: 'darkpool', label: 'Dark Pool', icon: '◐', description: '暗池流动' },
];

function toneClasses(score: number | null, weight: number, isMock: boolean, error: string | null | undefined): {
  bg: string;
  bar: string;
  text: string;
} {
  if (error) return { bg: 'border-[var(--color-danger)]/40', bar: 'bg-[var(--color-danger)]', text: 'text-[var(--color-danger)]' };
  if (isMock) return { bg: 'border-[var(--color-warning)]/40', bar: 'bg-[var(--color-warning)]', text: 'text-[var(--color-warning)]' };
  const pct = score == null ? 0 : score / weight;
  if (pct >= 0.66) return { bg: 'border-[var(--color-danger)]/40', bar: 'bg-[var(--color-danger)]', text: 'text-[var(--color-danger)]' };
  if (pct >= 0.33) return { bg: 'border-[var(--color-warning)]/40', bar: 'bg-[var(--color-warning)]', text: 'text-[var(--color-warning)]' };
  return { bg: 'border-[var(--color-success)]/40', bar: 'bg-[var(--color-success)]', text: 'text-[var(--color-success)]' };
}

export function DimensionScoreCards({
  dimensions,
  loading,
}: {
  dimensions: DimensionScore[];
  loading?: boolean;
}) {
  const byKey = new Map(dimensions.map((d) => [d.dimension, d]));
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {DIMENSIONS.map((dim) => {
        const data = byKey.get(dim.key);
        const score = data?.score ?? null;
        const weight = data?.weight ?? 1;
        const isMock = data?.is_mock ?? false;
        const error = data?.error ?? null;
        const tone = toneClasses(score, weight, isMock, error);
        const pct = score == null ? 0 : Math.min(100, Math.round((score / weight) * 100));
        return (
          <div
            key={dim.key}
            className={cn('msr-card flex flex-col gap-2 border', tone.bg)}
            role="group"
            aria-label={`${dim.label} ${dim.description}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl leading-none opacity-80" aria-hidden>{dim.icon}</span>
                <div>
                  <div className="text-sm font-semibold">{dim.label}</div>
                  <div className="text-[10px] text-[var(--color-text-muted)]">{dim.description}</div>
                </div>
              </div>
              {isMock && (
                <span
                  className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-warning)] bg-[var(--color-warning)]/15 px-1.5 py-0.5 rounded"
                  title="该维度当前使用模拟数据"
                >
                  MOCK
                </span>
              )}
            </div>

            {loading ? (
              <div className="h-8 w-16 bg-[var(--color-border)] rounded animate-pulse" />
            ) : (
              <div className="flex items-baseline gap-1">
                <span className={cn('msr-number text-2xl', tone.text)}>
                  {fmtNum(score, 2)}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">/ {weight.toFixed(1)}</span>
              </div>
            )}

            <div
              className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded overflow-hidden"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={weight}
              aria-valuenow={score ?? 0}
              aria-label={`${dim.label} 进度`}
            >
              <div
                className={cn('h-full transition-all duration-300', tone.bar)}
                style={{ width: `${pct}%` }}
              />
            </div>

            {error && (
              <div className="text-[10px] text-[var(--color-danger)] font-mono truncate" title={error}>
                ✕ {error}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}