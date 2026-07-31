/**
 * 全局 ErrorToast（监听 msr-api-error / msr-ws-status）
 * - 右下角浮动
 * - 最多 3 条同时显示，5 秒自动消失
 * - 可点击关闭
 */
import { useEffect, useState } from 'react';
import { apiErrorEventName } from '@/lib/api/client';
import { wsStatusEventName } from '@/lib/ws/WebSocketProvider';
import type { ApiError } from '@/lib/api/types';
import { cn } from '@/lib/utils/cn';

interface ToastItem {
  id: number;
  tone: 'info' | 'warning' | 'danger';
  title: string;
  detail?: string;
}

let nextId = 1;

export function ErrorToast() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    const onApiError = (ev: Event) => {
      const detail = (ev as CustomEvent<ApiError>).detail;
      const tone: ToastItem['tone'] = detail.status >= 500 ? 'danger' : 'warning';
      const title = `${detail.status || '网络'} ${detail.code}`;
      const item: ToastItem = {
        id: nextId++,
        tone,
        title,
        detail: `${detail.message} · ${detail.url}`,
      };
      setItems((prev) => [...prev, item].slice(-3));
    };

    const onWsStatus = (ev: Event) => {
      const state = (ev as CustomEvent<string>).detail;
      if (state === 'closed' || state === 'reconnecting') {
        const item: ToastItem = {
          id: nextId++,
          tone: 'warning',
          title: '实时连接中断',
          detail: state === 'reconnecting' ? '正在重连...' : '数据可能为缓存值',
        };
        setItems((prev) => [...prev, item].slice(-3));
      }
    };

    window.addEventListener(apiErrorEventName, onApiError);
    window.addEventListener(wsStatusEventName, onWsStatus);
    return () => {
      window.removeEventListener(apiErrorEventName, onApiError);
      window.removeEventListener(wsStatusEventName, onWsStatus);
    };
  }, []);

  useEffect(() => {
    if (items.length === 0) return;
    const timers = items.map((item) =>
      setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== item.id)), 5000),
    );
    return () => timers.forEach(clearTimeout);
  }, [items]);

  if (items.length === 0) return null;

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm"
      role="region"
      aria-label="通知"
    >
      {items.map((item) => (
        <div
          key={item.id}
          role={item.tone === 'danger' ? 'alert' : 'status'}
          className={cn(
            'rounded-md border px-4 py-3 shadow-md backdrop-blur',
            'animate-in fade-in slide-in-from-right-4',
            item.tone === 'danger' && 'border-[var(--color-danger)]/40 bg-[var(--color-danger)]/15',
            item.tone === 'warning' && 'border-[var(--color-warning)]/40 bg-[var(--color-warning)]/15',
            item.tone === 'info' && 'border-[var(--color-info)]/40 bg-[var(--color-info)]/15',
          )}
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm">{item.title}</div>
              {item.detail && <div className="text-xs opacity-80 mt-0.5 break-all">{item.detail}</div>}
            </div>
            <button
              type="button"
              onClick={() => setItems((prev) => prev.filter((i) => i.id !== item.id))}
              className="text-sm opacity-70 hover:opacity-100 rounded focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]"
              aria-label="关闭通知"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}