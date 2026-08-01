/**
 * 顶部导航栏
 * - 页面标题（动态）
 * - Last update timestamp
 * - Alert level badge
 * - Theme toggle（light/dark）+ collapse sidebar
 * - 移动端 hamburger 按钮
 */
import { useLocation } from 'react-router-dom';
import { useUIStore, applySparkTheme } from '@/lib/stores/ui';
import { useDashboard, useLatestSignal } from '@/lib/hooks/useDashboard';
import { fmtClock, fmtRelative, levelLabel, levelTone } from '@/lib/utils/format';
import { useEffect } from 'react';
import { cn } from '@/lib/utils/cn';

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard · 共振指挥中心',
  '/gex': 'GEX · 期权伽马暴露',
  '/vix': 'VIX · 波动率期限结构',
  '/crypto': 'Crypto · 加密衍生品',
  '/darkpool': 'Dark Pool · 暗池流动',
  '/signals': 'Signals · 警报历史',
  '/analysis': 'Analysis · LLM 增强分析',
  '/system': 'System · 健康与诊断',
  '/settings': 'Settings · 运行时配置',
};

function findTitle(pathname: string): string {
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname];
  const match = Object.keys(ROUTE_TITLES).find((k) => k !== '/' && pathname.startsWith(k));
  return match ? ROUTE_TITLES[match] : 'MSR';
}

interface TopBarProps {
  onMobileMenuToggle?: () => void;
  showMobileMenu?: boolean;
}

export function TopBar({ onMobileMenuToggle, showMobileMenu = false }: TopBarProps) {
  const loc = useLocation();
  const theme = useUIStore((s) => s.theme);
  const style = useUIStore((s) => s.style);
  const setTheme = useUIStore((s) => s.setTheme);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  // FIX-43: read the ``sidebarCollapsed`` flag so ``aria-expanded``
  // reflects reality, not the always-truthy bare attribute.
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);
  const lastUpdateAt = useUIStore((s) => s.lastUpdateAt);

  const { data: dashboard } = useDashboard();
  const { data: latestSignal } = useLatestSignal();

  useEffect(() => {
    applySparkTheme(theme, style);
  }, [theme, style]);

  const alertLevel = (() => {
    const raw = dashboard?.alert_level ?? latestSignal?.alert_level ?? null;
    if (raw == null) return null;
    const n = typeof raw === 'number' ? raw : Number(raw);
    return Number.isFinite(n) ? n : null;
  })();

  return (
    <header
      className="flex items-center justify-between gap-4 h-[var(--topbar-height)] px-4 bg-[var(--color-bg-container)] border-b border-[var(--color-border)]"
      role="banner"
    >
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile menu toggle */}
        {showMobileMenu && (
          <button
            type="button"
            onClick={onMobileMenuToggle}
            className="p-1.5 rounded hover:bg-[var(--color-bg-elevated)] focus-visible:outline-2 focus-visible:outline-[var(--color-primary)] md:hidden"
            aria-label="打开导航菜单"
          >
            <span className="text-base">≡</span>
          </button>
        )}
        {/* Desktop sidebar toggle */}
        <button
          type="button"
          onClick={toggleSidebar}
          className="p-1.5 rounded hover:bg-[var(--color-bg-elevated)] focus-visible:outline-2 focus-visible:outline-[var(--color-primary)] hidden md:inline-flex"
          aria-label="切换侧边栏"
          // FIX-43: ``aria-expanded`` requires a string value ("true" /
          // "false"). The bare ``aria-expanded`` attribute evaluates to
          // ``true`` always in HTML, which screen readers always read
          // as "expanded" — even when the sidebar is collapsed.
          aria-expanded={!sidebarCollapsed}
        >
          <span className="text-base">≡</span>
        </button>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)] truncate">
          {findTitle(loc.pathname)}
        </h2>
      </div>

      <div className="flex items-center gap-3 text-xs text-[var(--color-text-secondary)]">
        {/* Alert level badge */}
        {alertLevel != null && alertLevel > 0 && (
          <span
            className={cn(
              'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider',
              levelTone(alertLevel) === 'danger' && 'bg-[var(--color-danger)]/20 text-[var(--color-danger)]',
              levelTone(alertLevel) === 'warning' && 'bg-[var(--color-warning)]/20 text-[var(--color-warning)]',
              levelTone(alertLevel) === 'info' && 'bg-[var(--color-info)]/20 text-[var(--color-info)]',
            )}
            role="status"
            aria-label={levelLabel(alertLevel)}
          >
            {levelLabel(alertLevel)}
          </span>
        )}

        {/* Last update */}
        <span className="font-mono hidden sm:inline" title={lastUpdateAt ?? ''}>
          {lastUpdateAt ? `更新 ${fmtClock(lastUpdateAt)} · ${fmtRelative(lastUpdateAt)}` : '尚无更新'}
        </span>

        {/* Theme toggle */}
        <button
          type="button"
          onClick={() => setTheme(theme.startsWith('dark') ? 'light' : 'dark')}
          className="p-1.5 rounded hover:bg-[var(--color-bg-elevated)] focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]"
          aria-label="切换主题"
          title={`切换到 ${theme.startsWith('dark') ? '浅色' : '深色'} 主题`}
        >
          <span aria-hidden>{theme.startsWith('dark') ? '☀' : '☾'}</span>
        </button>
      </div>
    </header>
  );
}