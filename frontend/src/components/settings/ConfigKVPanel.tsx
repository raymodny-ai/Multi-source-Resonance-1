/**
 * ConfigKVPanel — 系统配置 KV 表（alert thresholds / pipeline / retention）
 */
import { useMemo, useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { Button, Input } from 'sparkdesign';
import {
  useConfigList,
  useRestoreDefaults,
  useUpdateConfigKV,
} from '@/lib/hooks/useConfig';
import type { ConfigItem } from '@/lib/api/types';
import { cn } from '@/lib/utils/cn';
import { fmtTime } from '@/lib/utils/format';

type Filter = 'all' | 'alert' | 'pipeline' | 'retention' | 'notification' | 'other';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'alert', label: '告警' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'retention', label: '保留' },
  { value: 'notification', label: '通知' },
  { value: 'other', label: '其他' },
];

function classify(key: string): Filter {
  const k = key.toLowerCase();
  if (k.includes('alert') || k.includes('threshold') || k.includes('level_')) return 'alert';
  if (k.includes('pipeline') || k.includes('interval') || k.includes('cycle')) return 'pipeline';
  if (k.includes('retention') || k.includes('days')) return 'retention';
  if (k.includes('notif') || k.includes('telegram')) return 'notification';
  return 'other';
}

export function ConfigKVPanel() {
  const { data, isLoading, error } = useConfigList();
  const update = useUpdateConfigKV();
  const restore = useRestoreDefaults();
  const [filter, setFilter] = useState<Filter>('all');
  const [editing, setEditing] = useState<{ key: string; value: string } | null>(null);

  const items = data?.configs ?? [];

  const filtered = useMemo(
    () => (filter === 'all' ? items : items.filter((c) => classify(c.key) === filter)),
    [items, filter],
  );

  const counts = useMemo(() => {
    const c = { all: items.length, alert: 0, pipeline: 0, retention: 0, notification: 0, other: 0 };
    items.forEach((it) => {
      const k = classify(it.key);
      c[k] += 1;
    });
    return c;
  }, [items]);

  const handleSave = async (item: ConfigItem) => {
    if (!editing || editing.key !== item.key) return;
    try {
      await update.mutateAsync({ key: item.key, value: editing.value });
      setEditing(null);
    } catch {
      /* ErrorToast handles */
    }
  };

  const handleRestore = async () => {
    if (!confirm('确认恢复所有 config 为默认值？此操作不可撤销。')) return;
    try {
      await restore.mutateAsync();
      setEditing(null);
    } catch {
      /* ErrorToast handles */
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">运行时配置 KV</h3>
            <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
              {items.length} 条
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1" role="tablist" aria-label="配置分类">
              {FILTERS.map((f) => {
                const active = filter === f.value;
                return (
                  <button
                    key={f.value}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setFilter(f.value)}
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]',
                      active
                        ? 'bg-[var(--color-primary)]/15 text-[var(--color-primary)]'
                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]',
                    )}
                  >
                    {f.label}
                    <span className="text-[10px] opacity-70 font-mono">{counts[f.value]}</span>
                  </button>
                );
              })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRestore}
              disabled={restore.isPending}
              aria-label="恢复默认值"
            >
              {restore.isPending ? '恢复中...' : '恢复默认'}
            </Button>
          </div>
        </div>

        {error && (
          <div className="text-xs text-[var(--color-danger)] py-2">
            配置加载失败：{(error as Error).message}
          </div>
        )}

        {isLoading && items.length === 0 ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-[100px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            {items.length === 0 ? '暂无配置项' : '该分类下无配置'}
          </div>
        ) : (
          <div className="overflow-x-auto -mx-2">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <th className="px-2 py-2 font-medium">Key</th>
                  <th className="px-2 py-2 font-medium">Value</th>
                  <th className="px-2 py-2 font-medium">Description</th>
                  <th className="px-2 py-2 font-medium">Updated</th>
                  <th className="px-2 py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const isEditing = editing?.key === item.key;
                  return (
                    <tr
                      key={item.key}
                      className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-elevated)]/50"
                    >
                      <td className="px-2 py-1.5 font-mono text-[var(--color-text-primary)] font-semibold align-top">
                        {item.key}
                      </td>
                      <td className="px-2 py-1.5 align-top">
                        {isEditing ? (
                          <Input
                            value={editing.value}
                            onChange={(e) => setEditing({ ...editing, value: e.target.value })}
                            size="sm"
                            className="w-40 font-mono"
                            aria-label={`编辑 ${item.key}`}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSave(item);
                              if (e.key === 'Escape') setEditing(null);
                            }}
                          />
                        ) : (
                          <code className="font-mono text-xs">{item.value}</code>
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-[var(--color-text-muted)] text-[11px] align-top">
                        {item.description ?? <span className="opacity-50">—</span>}
                      </td>
                      <td className="px-2 py-1.5 font-mono text-[10px] text-[var(--color-text-muted)] align-top">
                        {item.updated_at ? fmtTime(item.updated_at) : '—'}
                      </td>
                      <td className="px-2 py-1.5 text-right align-top">
                        {isEditing ? (
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleSave(item)}
                              disabled={update.isPending}
                              aria-label="保存"
                            >
                              {update.isPending ? '...' : '保存'}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setEditing(null)}
                              aria-label="取消"
                            >
                              取消
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditing({ key: item.key, value: item.value })}
                            aria-label={`编辑 ${item.key}`}
                          >
                            编辑
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}