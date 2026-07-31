/**
 * Hawkes 模型分枝比卡片
 * - >1 表示自激过程（高活跃期）
 * - <1 表示均值回归
 */
import { fmtNum } from '@/lib/utils/format';

export function HawkesIntensityCard({
  branchingRatio,
  loading,
}: {
  branchingRatio: number | null;
  loading?: boolean;
}) {
  const ratio = branchingRatio ?? 0;
  const tone =
    ratio >= 1.2 ? 'text-[var(--color-danger)]' :
    ratio >= 1.0 ? 'text-[var(--color-warning)]' :
    ratio >= 0.5 ? 'text-[var(--color-info)]' :
    'text-[var(--color-success)]';
  const label =
    ratio >= 1.2 ? '强自激 · 警报密集' :
    ratio >= 1.0 ? '自激 · 活跃区间' :
    ratio >= 0.5 ? '均值回归' :
    '冷却期';

  return (
    <div className="msr-card flex flex-col gap-2" role="group" aria-label="Hawkes 自激过程分枝比">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Hawkes 分枝比</h3>
        <span className="text-[10px] text-[var(--color-text-muted)]">自激过程</span>
      </div>
      {loading ? (
        <div className="h-8 w-20 bg-[var(--color-border)] rounded animate-pulse" />
      ) : (
        <div className="flex items-baseline gap-2">
          <span className={`msr-number text-3xl ${tone}`}>{fmtNum(branchingRatio, 2, '—')}</span>
          <span className="text-xs text-[var(--color-text-muted)]">/ 1.0</span>
        </div>
      )}
      <div className={`text-xs ${tone}`} aria-live="polite">{label}</div>
      {/* visual bar */}
      <div className="h-1.5 w-full bg-[var(--color-bg-elevated)] rounded overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            ratio >= 1.2 ? 'bg-[var(--color-danger)]' :
            ratio >= 1.0 ? 'bg-[var(--color-warning)]' :
            ratio >= 0.5 ? 'bg-[var(--color-info)]' :
            'bg-[var(--color-success)]'
          }`}
          style={{ width: `${Math.min(100, Math.round(ratio * 50))}%` }}
        />
      </div>
    </div>
  );
}