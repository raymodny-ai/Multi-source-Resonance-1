/**
 * PrometheusMetricsCard — 嵌入式 Prometheus 指标展示
 */
import { useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { useMetricsSummary, usePrometheusMetrics } from '@/lib/hooks/useSystem';
import { fmtNum } from '@/lib/utils/format';

export function MetricsSummaryCard() {
  const { data, isLoading, error } = useMetricsSummary();
  const [showRaw, setShowRaw] = useState(false);

  const cpuOption = useMemo(() => {
    if (!data) return {};
    const pipelineRunning = data.pipeline.running ? 1 : 0;
    return {
      tooltip: {},
      radar: {
        indicator: [
          { name: 'Pipeline 运行', max: 1 },
          { name: 'Event Bus', max: 100 },
          { name: 'Cycles/min', max: 10 },
          { name: 'DB 健康', max: 100 },
        ],
        radius: '60%',
        axisName: { color: '#a0a0b5', fontSize: 11 },
        splitArea: { areaStyle: { color: ['rgba(99,102,241,0.04)', 'rgba(99,102,241,0.02)'] } },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color: '#6366f1', width: 2 },
          areaStyle: { color: 'rgba(99,102,241,0.18)' },
          itemStyle: { color: '#6366f1' },
          data: [
            {
              value: [
                pipelineRunning,
                Object.values(data.event_bus ?? {}).reduce<number>((s, v) => s + (typeof v === 'number' ? v : 0), 0),
                data.pipeline.cycles / Math.max(1, data.uptime_seconds / 60),
                100,
              ],
              name: '健康度',
            },
          ],
        },
      ],
    };
  }, [data]);

  if (isLoading && !data) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-40 bg-[var(--color-border)] rounded animate-pulse mb-3" />
          <div className="h-[200px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card>
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold mb-2">Prometheus 指标</h3>
          <div className="text-xs text-[var(--color-danger)] py-3">
            加载失败：{(error as Error).message}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const tableCounts = Object.entries(data.database.table_counts ?? {}).slice(0, 8);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">Prometheus · Metrics Summary</h3>
          <button
            type="button"
            onClick={() => setShowRaw((v) => !v)}
            className="text-[10px] text-[var(--color-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--color-primary)] rounded"
            aria-expanded={showRaw}
          >
            {showRaw ? '隐藏' : '显示'} 表行数
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div>
            <ReactECharts option={cpuOption} style={{ height: 200, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
          </div>
          <div className="grid grid-cols-2 gap-2 content-start">
            <div className="rounded bg-[var(--color-bg-elevated)] p-2">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase">Cycles</div>
              <div className="msr-number text-base">{fmtNum(data.pipeline.cycles, 0)}</div>
            </div>
            <div className="rounded bg-[var(--color-bg-elevated)] p-2">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase">Fetchers</div>
              <div className="msr-number text-base">{data.pipeline.fetchers}</div>
            </div>
            <div className="rounded bg-[var(--color-bg-elevated)] p-2">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase">DB Size</div>
              <div className="msr-number text-base">{data.database.size_mb.toFixed(1)} MB</div>
            </div>
            <div className="rounded bg-[var(--color-bg-elevated)] p-2">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase">Uptime</div>
              <div className="msr-number text-base">{fmtNum(data.uptime_seconds / 3600, 1)}h</div>
            </div>
          </div>
        </div>

        {showRaw && (
          <div className="mt-3 border-t border-[var(--color-border)] pt-3">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-2">
              数据库表行数（Top 8）
            </div>
            <ul className="grid grid-cols-2 gap-1">
              {tableCounts.map(([name, count]) => (
                <li
                  key={name}
                  className="flex items-center justify-between text-[11px] font-mono border-b border-[var(--color-border)]/50 py-0.5"
                >
                  <span className="truncate">{name}</span>
                  <span className="text-[var(--color-text-muted)]">{count.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PrometheusRawCard() {
  const { data, isLoading } = usePrometheusMetrics(true);
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">Prometheus 原始指标</h3>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            /api/metrics
          </span>
        </div>
        {isLoading ? (
          <div className="h-[180px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        ) : (
          <pre
            className="text-[10px] font-mono whitespace-pre-wrap max-h-[300px] overflow-y-auto p-2 rounded bg-[var(--color-bg-elevated)]"
            aria-label="Prometheus 原始指标"
          >
            {data ?? '(空)'}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}