/**
 * WS 连接状态徽章（Sidebar 底部使用）
 */
import { useUIStore } from '@/lib/stores/ui';
import { cn } from '@/lib/utils/cn';

const labelMap = {
  open: 'WS: 已连接',
  connecting: 'WS: 连接中',
  reconnecting: 'WS: 重连中',
  closed: 'WS: 已断开',
} as const;

const dotClassMap = {
  open: 'bg-[var(--color-success)] animate-pulse-dot',
  connecting: 'bg-[var(--color-warning)]',
  reconnecting: 'bg-[var(--color-warning)] animate-pulse-dot',
  closed: 'bg-[var(--color-danger)]',
} as const;

export function WSStatusIndicator({ collapsed = false }: { collapsed?: boolean }) {
  const wsState = useUIStore((s) => s.wsState);
  return (
    <div
      className={cn(
        'flex items-center gap-2 text-xs',
        'text-[var(--color-text-secondary)]',
        collapsed && 'justify-center',
      )}
      role="status"
      aria-live="polite"
      aria-label={labelMap[wsState]}
    >
      <span className={cn('inline-block h-2 w-2 rounded-full', dotClassMap[wsState])} aria-hidden />
      {!collapsed && <span>{labelMap[wsState]}</span>}
    </div>
  );
}