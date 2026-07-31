/**
 * 侧边栏导航
 * - Logo + 分组菜单 + WS 状态徽章
 * - 折叠态（icon-only）由 useUIStore.sidebarCollapsed 控制
 */
import { NavLink } from 'react-router-dom';
import { useUIStore } from '@/lib/stores/ui';
import { WSStatusIndicator } from './WSStatusIndicator';
import { cn } from '@/lib/utils/cn';

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: '监控',
    items: [
      { to: '/', label: 'Dashboard', icon: '◉' },
      { to: '/gex', label: 'GEX', icon: '◈' },
      { to: '/vix', label: 'VIX', icon: '◈' },
      { to: '/crypto', label: 'Crypto', icon: '◈' },
      { to: '/darkpool', label: 'Dark Pool', icon: '◈' },
    ],
  },
  {
    title: '信号',
    items: [
      { to: '/signals', label: 'Signals', icon: '◈' },
      { to: '/analysis', label: 'Analysis', icon: '◈' },
    ],
  },
  {
    title: '运维',
    items: [
      { to: '/system', label: 'System', icon: '◈' },
      { to: '/settings', label: 'Settings', icon: '◈' },
    ],
  },
];

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-[var(--color-bg-container)] border-r border-[var(--color-border)] transition-all duration-200',
        collapsed ? 'w-[var(--sidebar-width-collapsed)]' : 'w-[var(--sidebar-width)]',
      )}
      aria-label="主导航"
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 h-[var(--topbar-height)] border-b border-[var(--color-border)]">
        <span className="text-2xl leading-none" aria-hidden>◈</span>
        {!collapsed && <span className="font-semibold tracking-tight">MSR</span>}
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && (
              <div className="px-4 text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
                {group.title}
              </div>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-4 py-2 text-sm rounded-r-md mx-1 transition-colors',
                        isActive
                          ? 'bg-[var(--color-primary)]/15 text-[var(--color-primary)] font-medium'
                          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text-primary)]',
                      )
                    }
                    title={collapsed ? item.label : undefined}
                    aria-label={item.label}
                  >
                    <span className="text-base w-5 text-center" aria-hidden>{item.icon}</span>
                    {!collapsed && <span>{item.label}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer: WS status + version */}
      <div className="border-t border-[var(--color-border)] p-3 space-y-2">
        <WSStatusIndicator collapsed={collapsed} />
        {!collapsed && (
          <div className="text-[10px] text-[var(--color-text-muted)] font-mono">v4.0.0</div>
        )}
      </div>
    </aside>
  );
}