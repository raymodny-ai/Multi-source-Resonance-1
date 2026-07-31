/**
 * 通用 Alert 横幅（错误 / Mock 警告 / 离线降级）
 * 用法：
 *   <AlertBanner tone="danger" title="..." dismissible onClose={...}>...</AlertBanner>
 */
import { useEffect, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

export type AlertTone = 'info' | 'success' | 'warning' | 'danger';

const toneClasses: Record<AlertTone, string> = {
  info: 'border-[var(--color-info)]/40 bg-[var(--color-info)]/10 text-[var(--color-text-primary)]',
  success: 'border-[var(--color-success)]/40 bg-[var(--color-success)]/10 text-[var(--color-text-primary)]',
  warning: 'border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 text-[var(--color-text-primary)]',
  danger: 'border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 text-[var(--color-text-primary)]',
};

const iconMap: Record<AlertTone, string> = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  danger: '✕',
};

interface AlertBannerProps {
  tone: AlertTone;
  title?: string;
  children?: ReactNode;
  dismissible?: boolean;
  onClose?: () => void;
  className?: string;
  role?: 'alert' | 'status';
}

export function AlertBanner({
  tone,
  title,
  children,
  dismissible = false,
  onClose,
  className,
  role = 'alert',
}: AlertBannerProps) {
  const [visible, setVisible] = useState(true);
  if (!visible) return null;
  return (
    <div
      role={role}
      className={cn(
        'flex items-start gap-3 rounded-md border px-4 py-3 animate-slide-in-up',
        toneClasses[tone],
        className,
      )}
    >
      <span className="text-lg leading-none" aria-hidden>{iconMap[tone]}</span>
      <div className="flex-1 min-w-0">
        {title && <div className="font-semibold mb-1">{title}</div>}
        {children && <div className="text-sm opacity-90">{children}</div>}
      </div>
      {dismissible && (
        <button
          type="button"
          onClick={() => { setVisible(false); onClose?.(); }}
          className="text-sm opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] rounded"
          aria-label="关闭提示"
        >
          ✕
        </button>
      )}
    </div>
  );
}

/** 自动消失（毫秒） */
export function AutoDismissAlert(props: AlertBannerProps & { duration?: number }) {
  const { duration = 8000, onClose, ...rest } = props;
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(() => { setVisible(false); onClose?.(); }, duration);
    return () => clearTimeout(t);
  }, [duration, onClose, visible]);
  if (!visible) return null;
  return <AlertBanner {...rest} />;
}