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
  /** 从 data 提取分数的字段名 */
  scoreKey: keyof Pick<
    DashboardDataNormalized,
    'gex_score' | 'vix_score' | 'crypto_score' | 'darkpool_score'
  >;
}

// 各维度分数统一为 0-100 归一化尺度（与后端 scoring.calculate_score 一致）。
// 旧版把聚合权重（GEX 2.5/VIX 1.5/Crypto 2.0/Darkpool 2.0，和为 RAW_MAX=8.0）误当
// 成维度满分来显示 "/ 2.5" 并除以 weight 算进度条，导致 VIX 100/1.5=66% 等错误显示。
// 权重只用于后端聚合 total_score，不参与单维度展示 —— 这里满分统一为 100。
const SCORE_MAX = 100;

const DIMENSIONS: DimensionDef[] = [
  { key: 'gex', label: 'GEX', icon: 'Γ', description: '期权伽马暴露', scoreKey: 'gex_score' },
  { key: 'vix', label: 'VIX', icon: 'σ', description: '波动率期限结构', scoreKey: 'vix_score' },
  { key: 'crypto', label: 'Crypto', icon: '₿', description: '加密衍生品', scoreKey: 'crypto_score' },
  { key: 'darkpool', label: 'Dark Pool', icon: '◐', description: '暗池流动', scoreKey: 'darkpool_score' },
];

interface ToneClasses {
  border: string;
  bar: string;
  text: string;
}

function toneClasses(score: number | null, isMock: boolean): ToneClasses {
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
  // 分数已是 0-100，按 100 算比例
  const pct = score / SCORE_MAX;
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
        const tone = toneClasses(score, isMock);
        const pct = score == null ? 0 : Math.min(100, Math.round((score / SCORE_MAX) * 100));
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
                <span className="text-xs text-[var(--color-text-muted)]">/ {SCORE_MAX.toFixed(0)}</span>
              </div>
            )}

            <div
              className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded overflow-hidden"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={SCORE_MAX}
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
