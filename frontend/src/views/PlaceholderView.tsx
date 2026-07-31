/**
 * 占位页面（P2 / P3 阶段实现）
 * - 用于 GEX / VIX / Crypto / Dark Pool / Analysis / System / Settings
 * - 在 P1 阶段提供一个一致的"敬请期待"占位
 */
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';

interface PlaceholderViewProps {
  title: string;
  description: string;
  milestone: 'P2' | 'P3' | 'P4';
  features: string[];
}

export function PlaceholderView({ title, description, milestone, features }: PlaceholderViewProps) {
  return (
    <>
      <PageHeader title={title} description={description} />

      <AlertBanner tone="info" title={`该页面将在 ${milestone} 阶段交付`}>
        本 P1 阶段只交付 App Shell + Dashboard + Signals。其余页面在后续 milestone 中按 PRD 实现。
      </AlertBanner>

      <div className="msr-card mt-4 p-6">
        <h3 className="text-sm font-semibold mb-3">计划交付能力</h3>
        <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          {features.map((f, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-[var(--color-primary)] mt-0.5" aria-hidden>◆</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
