/**
 * DataSourcesPanel — 数据源启用 / 禁用 / API Key 状态
 */
import { useMemo, useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { Button, Input, Switch } from 'sparkdesign';
import { useSourcesConfig, useUpdateSourceConfig } from '@/lib/hooks/useConfig';
import type { SourceConfig } from '@/lib/api/config';
import { cn } from '@/lib/utils/cn';

type Filter = 'all' | 'enabled' | 'disabled' | 'mock' | 'no-key';

export function DataSourcesPanel() {
  const { data, isLoading, error } = useSourcesConfig();
  const update = useUpdateSourceConfig();
  const [filter, setFilter] = useState<Filter>('all');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [keyValue, setKeyValue] = useState('');

  const sources = data ?? [];

  const filtered = useMemo(() => {
    if (filter === 'all') return sources;
    if (filter === 'enabled') return sources.filter((s) => s.enabled);
    if (filter === 'disabled') return sources.filter((s) => !s.enabled);
    if (filter === 'mock') return sources.filter((s) => s.mock_mode);
    if (filter === 'no-key') return sources.filter((s) => !s.has_api_key);
    return sources;
  }, [sources, filter]);

  const counts = useMemo(
    () => ({
      all: sources.length,
      enabled: sources.filter((s) => s.enabled).length,
      disabled: sources.filter((s) => !s.enabled).length,
      mock: sources.filter((s) => s.mock_mode).length,
      'no-key': sources.filter((s) => !s.has_api_key).length,
    }),
    [sources],
  );

  const handleToggle = async (src: SourceConfig, enabled: boolean) => {
    try {
      await update.mutateAsync({ name: src.name, enabled });
    } catch {
      /* ErrorToast handles */
    }
  };

  const handleSaveKey = async (src: SourceConfig) => {
    try {
      await update.mutateAsync({ name: src.name, api_key: keyValue });
      setEditingKey(null);
      setKeyValue('');
    } catch {
      /* ErrorToast handles */
    }
  };

  const FILTERS: { value: Filter; label: string }[] = [
    { value: 'all', label: '全部' },
    { value: 'enabled', label: '已启用' },
    { value: 'disabled', label: '已禁用' },
    { value: 'mock', label: 'Mock' },
    { value: 'no-key', label: '缺 Key' },
  ];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">数据源管理</h3>
            <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
              {sources.length} 个
            </span>
          </div>
          <div className="flex items-center gap-1" role="tablist" aria-label="数据源过滤">
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
        </div>

        {error && (
          <div className="text-xs text-[var(--color-danger)] py-2">
            数据源加载失败：{(error as Error).message}
          </div>
        )}

        {isLoading && sources.length === 0 ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-[80px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            无匹配数据源
          </div>
        ) : (
          <ul className="space-y-1 max-h-[320px] overflow-y-auto pr-2">
            {filtered.map((src) => {
              const isEditing = editingKey === src.name;
              return (
                <li
                  key={src.name}
                  className="flex items-center justify-between gap-2 py-2 border-t border-[var(--color-border)]/50 first:border-t-0"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <span
                      aria-hidden
                      className={cn(
                        'inline-block w-1.5 h-1.5 rounded-full shrink-0',
                        src.enabled ? 'bg-[var(--color-success)]' : 'bg-[var(--color-text-muted)]',
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-mono font-semibold truncate">{src.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        {src.mock_mode && (
                          <span className="inline-block px-1 py-0.5 rounded bg-[var(--color-warning)]/15 text-[var(--color-warning)] text-[9px] font-bold uppercase">
                            MOCK
                          </span>
                        )}
                        {src.has_api_key ? (
                          <span className="inline-block px-1 py-0.5 rounded bg-[var(--color-info)]/15 text-[var(--color-info)] text-[9px] font-bold uppercase">
                            KEY
                          </span>
                        ) : (
                          <span className="inline-block px-1 py-0.5 rounded bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)] text-[9px] font-bold uppercase">
                            NO-KEY
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isEditing ? (
                      <>
                        <Input
                          type="password"
                          value={keyValue}
                          onChange={(e) => setKeyValue(e.target.value)}
                          placeholder="API Key"
                          size="sm"
                          className="w-32 font-mono"
                          aria-label={`设置 ${src.name} 的 API Key`}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveKey(src);
                            if (e.key === 'Escape') setEditingKey(null);
                          }}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSaveKey(src)}
                          disabled={update.isPending}
                          aria-label="保存 Key"
                        >
                          保存
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingKey(null)}
                          aria-label="取消"
                        >
                          取消
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingKey(src.name);
                            setKeyValue('');
                          }}
                          aria-label={`设置 ${src.name} 的 API Key`}
                        >
                          {src.has_api_key ? '更新 Key' : '设置 Key'}
                        </Button>
                        <Switch
                          checked={src.enabled}
                          onCheckedChange={(v) => handleToggle(src, v)}
                          disabled={update.isPending}
                          aria-label={`启用 ${src.name}`}
                        />
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}