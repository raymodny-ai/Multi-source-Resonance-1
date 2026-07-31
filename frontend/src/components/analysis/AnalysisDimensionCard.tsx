/**
 * Analysis 子维度卡（gex / vix / crypto / darkpool 各显示派生布尔字段集合）
 */
import { Card, CardContent } from 'sparkdesign';
import type { AnalysisDimensionView } from '@/lib/api/analysis';
import { cn } from '@/lib/utils/cn';

interface Props {
  title: string;
  icon: string;
  view: AnalysisDimensionView | null;
  loading?: boolean;
}

const FLAG_LABELS: Record<string, string> = {
  long_gamma_dominant: 'Long-γ 主导',
  short_gamma_risk: 'Short-γ 风险',
  positive_carry: '正向 Carry',
  contango: 'Contango',
  backwardation: 'Backwardation',
  panic_premium_high: '高恐慌溢价',
  liquidation_event: '爆仓事件',
  funding_anomaly: 'Funding 异常',
  leverage_cleanup: '杠杆清理',
  bullish_divergence: '看涨背离',
  bearish_divergence: '看跌背离',
  institutional_accumulation: '机构累积',
  ma_recovery: 'MA 恢复',
};

export function AnalysisDimensionCard({ title, icon, view, loading }: Props) {
  if (loading || !view) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-24 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-5 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }
  const analysis = view.analysis ?? {};
  const keys = Object.keys(FLAG_LABELS);
  const triggered = keys.filter((k) => analysis[k] === true);
  const present = triggered.length > 0;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg opacity-80" aria-hidden>{icon}</span>
            <h3 className="text-sm font-semibold">{title}</h3>
          </div>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            {view.timestamp ? new Date(view.timestamp).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
          </span>
        </div>

        {!present ? (
          <div className="text-xs text-[var(--color-text-muted)] py-3 text-center">
            暂无触发特征
          </div>
        ) : (
          <ul className="space-y-1">
            {triggered.map((k) => (
              <li
                key={k}
                className={cn(
                  'flex items-center justify-between border-t border-[var(--color-border)] py-1.5 first:border-t-0',
                )}
              >
                <span className="text-xs">{FLAG_LABELS[k] ?? k}</span>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-warning)]" aria-label="触发" />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
