/**
 * 通用空状态（用于列表 / 图表 / 卡片）
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

interface Props {
  icon?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  height?: number | string;
  className?: string;
}

export function EmptyState({
  icon = '◌',
  title = '暂无数据',
  description,
  action,
  height = 120,
  className,
}: Props) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center text-center gap-2',
        className,
      )}
      style={{ minHeight: height }}
    >
      <div
        className="text-3xl text-[var(--color-text-muted)] opacity-60"
        aria-hidden
      >
        {icon}
      </div>
      {title && (
        <div className="text-sm font-semibold text-[var(--color-text-secondary)]">
          {title}
        </div>
      )}
      {description && (
        <div className="text-xs text-[var(--color-text-muted)] max-w-md">
          {description}
        </div>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/**
 * 错误状态（带 retry）
 */
import { Button } from 'sparkdesign';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = '加载失败',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center gap-2 py-6',
        className,
      )}
    >
      <div className="text-3xl text-[var(--color-danger)]" aria-hidden>✕</div>
      <div className="text-sm font-semibold text-[var(--color-danger)]">{title}</div>
      {message && (
        <div className="text-xs text-[var(--color-text-muted)] max-w-md break-all">
          {message}
        </div>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          重试
        </Button>
      )}
    </div>
  );
}

/**
 * 加载骨架屏
 */
export function Skeleton({
  height = 16,
  width = '100%',
  className,
  rounded = 'rounded',
}: {
  height?: number | string;
  width?: number | string;
  className?: string;
  rounded?: string;
}) {
  return (
    <div
      className={cn('msr-skeleton', rounded, className)}
      style={{ height, width }}
      aria-hidden
    />
  );
}