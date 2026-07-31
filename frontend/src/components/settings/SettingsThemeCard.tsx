/**
 * SettingsThemeCard — Spark 双维度主题切换（theme + style）
 * 直接驱动 useUIStore / applySparkTheme
 */
import { Card, CardContent } from 'sparkdesign';
import { useUIStore, type SparkTheme, type SparkStyle } from '@/lib/stores/ui';
import { cn } from '@/lib/utils/cn';

const THEMES: { value: SparkTheme; label: string; desc: string; preview: string }[] = [
  { value: 'light', label: 'Light', desc: '亮色 · 默认浅底', preview: '☀' },
  { value: 'dark', label: 'Dark', desc: '暗色 · 指挥中心默认', preview: '☾' },
  { value: 'light-parchment', label: 'Light + Parchment', desc: '亮色 + 羊皮纸质感', preview: '☀' },
  { value: 'dark-parchment', label: 'Dark + Parchment', desc: '暗色 + 羊皮纸质感', preview: '☾' },
];

const STYLES: { value: SparkStyle; label: string; desc: string }[] = [
  { value: 'neutral', label: 'Neutral', desc: '中性 · 平衡' },
  { value: 'compact', label: 'Compact', desc: '紧凑 · 高密度' },
  { value: 'soft', label: 'Soft', desc: '柔和 · 大圆角' },
  { value: 'sharp', label: 'Sharp', desc: '硬朗 · 直角' },
  { value: 'dense', label: 'Dense', desc: '致密 · 信息密度高' },
];

export function SettingsThemeCard() {
  const theme = useUIStore((s) => s.theme);
  const style = useUIStore((s) => s.style);
  const setTheme = useUIStore((s) => s.setTheme);
  const setStyle = useUIStore((s) => s.setStyle);

  return (
    <Card>
      <CardContent className="p-4">
        <h3 className="text-sm font-semibold mb-3">外观主题（Spark 双维度）</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
              Theme
            </div>
            <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="主题">
              {THEMES.map((t) => {
                const active = theme === t.value;
                return (
                  <button
                    key={t.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setTheme(t.value)}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded border transition-colors text-left focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]',
                      active
                        ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                        : 'border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]',
                    )}
                  >
                    <span aria-hidden className="text-lg">
                      {t.preview}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold">{t.label}</div>
                      <div className="text-[10px] text-[var(--color-text-muted)] truncate">
                        {t.desc}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
              Style
            </div>
            <div className="grid grid-cols-1 gap-1" role="radiogroup" aria-label="样式">
              {STYLES.map((s) => {
                const active = style === s.value;
                return (
                  <button
                    key={s.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setStyle(s.value)}
                    className={cn(
                      'flex items-center justify-between px-3 py-1.5 rounded border transition-colors text-left focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]',
                      active
                        ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                        : 'border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]',
                    )}
                  >
                    <div>
                      <div className="text-xs font-semibold">{s.label}</div>
                      <div className="text-[10px] text-[var(--color-text-muted)]">{s.desc}</div>
                    </div>
                    {active && <span className="text-[var(--color-primary)]">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}