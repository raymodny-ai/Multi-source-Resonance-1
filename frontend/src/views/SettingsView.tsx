/**
 * Settings 页面（运行时配置）
 * PRD §4.9
 *
 * Layout:
 * - 4 个概览卡 (config 条数 / 数据源状态 / mock 数量 / 当前主题)
 * - Spark 主题切换
 * - 系统配置 KV 表（可编辑）
 * - 数据源管理（启用 / 禁用 / 设置 Key）
 * - Bayesian 权重
 */
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { SettingsOverviewCards } from '@/components/settings/SettingsOverviewCards';
import { SettingsThemeCard } from '@/components/settings/SettingsThemeCard';
import { ConfigKVPanel } from '@/components/settings/ConfigKVPanel';
import { DataSourcesPanel } from '@/components/settings/DataSourcesPanel';
import { BayesianWeightsPanel } from '@/components/settings/BayesianWeightsPanel';
import {
  useConfigAuditLog,
  useConfigList,
  useSourcesConfig,
} from '@/lib/hooks/useConfig';
import { useQueryClient } from '@tanstack/react-query';
import { useUIStore } from '@/lib/stores/ui';
import { Card, CardContent } from 'sparkdesign';
import { fmtClock } from '@/lib/utils/format';

export function SettingsView() {
  const qc = useQueryClient();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  const [showAudit, setShowAudit] = useState(false);

  const config = useConfigList();
  const sources = useSourcesConfig();
  const audit = useConfigAuditLog();

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: ['config'] });
    setLastUpdateAt(new Date().toISOString());
  };

  const error = config.error ?? sources.error;

  return (
    <>
      <PageHeader
        title="Settings"
        description="运行时配置 · 系统 KV + 数据源 + Bayesian 权重 + 主题"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {error && (
        <AlertBanner tone="danger" title="Settings 数据加载失败">
          {(error as Error).message}
        </AlertBanner>
      )}

      {/* Overview */}
      <div className="mt-4">
        <SettingsOverviewCards />
      </div>

      {/* Theme + Weights row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <SettingsThemeCard />
        <BayesianWeightsPanel />
      </div>

      {/* Data sources */}
      <div className="mt-4">
        <DataSourcesPanel />
      </div>

      {/* KV config */}
      <div className="mt-4">
        <ConfigKVPanel />
      </div>

      {/* Audit log (collapsible) */}
      <div className="mt-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">配置变更审计</h3>
              <button
                type="button"
                onClick={() => setShowAudit((v) => !v)}
                className="text-[10px] text-[var(--color-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--color-primary)] rounded"
                aria-expanded={showAudit}
                aria-controls="settings-audit"
              >
                {showAudit ? '隐藏' : '显示'} 审计日志
              </button>
            </div>
            {showAudit && (
              <div id="settings-audit">
                {audit.isLoading && !audit.data ? (
                  <div className="h-[120px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
                ) : !audit.data || audit.data.length === 0 ? (
                  <div className="h-[80px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
                    暂无审计记录
                  </div>
                ) : (
                  <ul className="max-h-[200px] overflow-y-auto pr-2 text-[11px] font-mono">
                    {audit.data.slice(0, 30).map((row, idx) => {
                      const r = row as Record<string, unknown>;
                      const ts = (r.timestamp ?? r.ts ?? r.created_at ?? null) as string | null;
                      const key = (r.key ?? r.config_key ?? '—') as string;
                      const value = (r.value ?? r.new_value ?? '') as string;
                      const user = (r.user ?? r.actor ?? 'system') as string;
                      return (
                        <li
                          key={`${ts ?? idx}-${idx}`}
                          className="flex items-center justify-between border-t border-[var(--color-border)]/50 py-1 first:border-t-0"
                        >
                          <span className="text-[10px] text-[var(--color-text-muted)] w-14">
                            {ts ? fmtClock(ts) : '—'}
                          </span>
                          <span className="text-[var(--color-text-primary)] font-semibold flex-1 mx-2 truncate">
                            {key}
                          </span>
                          <span className="text-[var(--color-text-secondary)] truncate max-w-[120px]">
                            → {String(value)}
                          </span>
                          <span className="text-[10px] text-[var(--color-text-muted)] ml-2">{user}</span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        配置变更将立即生效 · 数据存于 <span className="text-[var(--color-primary)]">system_config</span> KV 表 ·{' '}
        上次更新：
        {config.dataUpdatedAt ? new Date(config.dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}