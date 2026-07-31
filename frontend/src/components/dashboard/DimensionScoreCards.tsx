/**
 * Dashboard 4 维度评分卡片（GEX / VIX / Crypto / Darkpool）
 * 直接从归一化后的 DashboardDataNormalized 传入四个分数 + mock 标记
 */
import type { DashboardDataNormalized } from '@/lib/api/dashboard';
import { fmtNum } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

interface DimensionDef {
  key: 'gex' | 'vix' | 'crypto' | 'darkpool';
  label: string;
  icon: string;
  description: string;
  /** 维度满分（用于进度条归一化） */
  weight: number;
  /** 从 data 提取分数的字段名 */
  scoreKey: keyof Pick<
    DashboardDataNormalized,
    'gex_score' | 'vix_score' | 'crypto_score' | 'darkpool_score'
  >;
}

const DIMENSIONS: DimensionDef[] = [
  { key: 'gex', label: 'GEX', icon: 'Γ', description: '期权伽马暴露', weight: 2.5, scoreKey: 'gex_score' },
  { key: 'vix', label: 'VIX', icon: 'σ', description: '波动率期限结构', weight: 1.5, scoreKey: 'vix_score' },
  { key: 'crypto', label: 'Crypto', icon: '₿', description: '加密衍生品', weight: 2.0, scoreKey: 'crypto_score' },
  { key: 'darkpool', label: 'Dark Pool', icon: '◐', description: '暗池流动', weight: 2.0, scoreKey: 'darkpool_score' },
];

interface ToneClasses {
  border: string;
  bar: string;
  text: string;
}

function toneClasses(score: number | null, weight: number, isMock: boolean): ToneClasses {
  if (isMock) {
    return {
      border: 'border-[var(--color-warning)]/40',
      bar: 'bg-[var(--color-warning)]',
      text: 'text-[var(--color-warning)]',
    };
  }
  if (score == null) {
    return {
      border: 'border-[var(--color-border)]',
      bar: 'bg-[var(--color-text-muted)]',
      text: 'text-[var(--color-text-muted)]',
    };
  }
  const pct = score / Math.max(0.0001, weight);
  if (pct >= 0.66) {
    return {
      border: 'border-[var(--color-danger)]/40',
      bar: 'bg-[var(--color-danger)]',
      text: 'text-[var(--color-danger)]',
    };
  }
  if (pct >= 0.33) {
    return {
      border: 'border-[var(--color-warning)]/40',
      bar: 'bg-[var(--color-warning)]',
      text: 'text-[var(--color-warning)]',
    };
  }
  return {
    border: 'border-[var(--color-success)]/40',
    bar: 'bg-[var(--color-success)]',
    text: 'text-[var(--color-success)]',
  };
}

export function DimensionScoreCards({
  data,
  loading,
}: {
  data: DashboardDataNormalized | null | undefined;
  loading?: boolean;
}) {
  const mockDims = data?.is_mock_dims ?? {
    gex: false,
    vix: false,
    crypto: false,
    darkpool: false,
  };
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {DIMENSIONS.map((dim) => {
        const isMock = mockDims[dim.key];
        const score = data?.[dim.scoreKey] ?? null;
        const tone = toneClasses(score, dim.weight, isMock);
        const pct = score == null ? 0 : Math.min(100, Math.round((score / dim.weight) * 100));
        return (
          <div
            key={dim.key}
            className={cn('msr-card flex flex-col gap-2 border', tone.border)}
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
                  {fmtNum(score, 2, '—')}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">/ {dim.weight.toFixed(1)}</span>
              </div>
            )}

            <div
              className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded overflow-hidden"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={dim.weight}
              aria-valuenow={score ?? 0}
              aria-label={`${dim.label} 进度`}
            >
              <div
                className={cn('h-full transition-all duration-300', tone.bar)}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
