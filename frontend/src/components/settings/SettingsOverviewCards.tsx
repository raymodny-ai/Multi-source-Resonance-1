/**
 * SettingsOverviewCards — Settings 概览（配置条数 / 数据源状态 / 主题）
 */
import { Card, CardContent } from 'sparkdesign';
import { useConfigList, useSourcesConfig } from '@/lib/hooks/useConfig';
import { useUIStore, type SparkTheme } from '@/lib/stores/ui';

export function SettingsOverviewCards() {
  const { data: configData } = useConfigList();
  const { data: sourcesData } = useSourcesConfig();
  const theme = useUIStore((s) => s.theme);

  const configCount = configData?.count ?? 0;
  const sourcesCount = sourcesData?.length ?? 0;
  const enabledCount = sourcesData?.filter((s) => s.enabled).length ?? 0;
  const mockCount = sourcesData?.filter((s) => s.mock_mode).length ?? 0;

  const themeLabel: Record<SparkTheme, string> = {
    'light': 'Light',
    'dark': 'Dark',
    'light-parchment': 'Light + Parchment',
    'dark-parchment': 'Dark + Parchment',
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            配置条目
          </div>
          <div className="msr-number text-xl">{configCount}</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            system_config
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            数据源
          </div>
          <div className="msr-number text-xl">
            {enabledCount} / {sourcesCount}
          </div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            启用 / 总数
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            Mock 数据源
          </div>
          <div className="msr-number text-xl text-[var(--color-warning)]">{mockCount}</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            降级运行
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
            当前主题
          </div>
          <div className="msr-number text-base">{themeLabel[theme]}</div>
          <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">
            在主题卡中切换
          </div>
        </CardContent>
      </Card>
    </div>
  );
}