/**
 * Analysis 综合卡片 — 最新多维度 LLM 增强分析
 * - 综合分数 + 警报级别 + 置信度
 * - text 主体（前端基于多维信号合成）
 * - 4 维度概览（gex/vix/crypto/darkpool）
 */
import { Card, CardContent } from 'sparkdesign';
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { fmtNum, fmtTime } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';
import type { AnalysisRecord } from '@/lib/api/analysis';

interface Props {
  record: AnalysisRecord | null;
  loading?: boolean;
}

const DIM_KEYS: Array<{ key: 'gex' | 'vix' | 'crypto' | 'darkpool'; label: string; icon: string }> = [
  { key: 'gex', label: 'GEX', icon: 'Γ' },
  { key: 'vix', label: 'VIX', icon: 'σ' },
  { key: 'crypto', label: 'Crypto', icon: '₿' },
  { key: 'darkpool', label: 'Darkpool', icon: '◐' },
];

export function AnalysisLatestCard({ record, loading }: Props) {
  const radarOption = useMemo(() => {
    if (!record) return {};
    const scoring = record.scoring;
    return {
      tooltip: {},
      radar: {
        indicator: [
          { name: 'GEX', max: scoring.max_score ?? 5 },
          { name: 'VIX', max: scoring.max_score ?? 5 },
          { name: 'Crypto', max: scoring.max_score ?? 5 },
          { name: 'Darkpool', max: scoring.max_score ?? 5 },
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
          symbolSize: 5,
          lineStyle: { color: '#6366f1', width: 2 },
          areaStyle: { color: 'rgba(99,102,241,0.18)' },
          itemStyle: { color: '#6366f1' },
          data: [
            {
              value: [
                scoring.gex_score ?? 0,
                scoring.vix_score ?? 0,
                scoring.crypto_score ?? 0,
                scoring.darkpool_score ?? 0,
              ],
              name: '维度分项',
            },
          ],
        },
      ],
    };
  }, [record]);

  if (loading || !record) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-32 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="h-[280px] bg-[var(--color-bg-elevated)] rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  const level = String(record.scoring.alert_level ?? 'NONE').toUpperCase();
  const levelTone =
    level === 'LEVEL_3'
      ? 'text-[var(--color-danger)] bg-[var(--color-danger)]/10 border-[var(--color-danger)]/40'
      : level === 'LEVEL_2'
        ? 'text-[var(--color-warning)] bg-[var(--color-warning)]/10 border-[var(--color-warning)]/40'
        : level === 'LEVEL_1'
          ? 'text-[var(--color-info)] bg-[var(--color-info)]/10 border-[var(--color-info)]/40'
          : 'text-[var(--color-text-muted)] bg-[var(--color-bg-elevated)] border-[var(--color-border)]';

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">综合分析 · 最新一次</h3>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider',
                levelTone,
              )}
            >
              {level}
            </span>
            <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
              {fmtTime(record.fetched_at)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mt-3">
          <div className="lg:col-span-2">
            <ReactECharts option={radarOption} style={{ height: 240, width: '100%' }} notMerge lazyUpdate opts={{ renderer: 'canvas' }} />
          </div>

          <div className="lg:col-span-3">
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5">
                <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">综合分</div>
                <div className="msr-number text-xl">
                  {fmtNum(record.scoring.total_score, 2)} <span className="text-[10px] text-[var(--color-text-muted)]">/ {fmtNum(record.scoring.max_score, 1)}</span>
                </div>
              </div>
              <div className="rounded bg-[var(--color-bg-elevated)] px-2 py-1.5">
                <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">置信度</div>
                <div className="msr-number text-xl">
                  {record.confidence != null ? `${(record.confidence * 100).toFixed(0)}%` : '—'}
                </div>
              </div>
            </div>

            <pre className="msr-card text-xs font-mono whitespace-pre-wrap leading-6 max-h-[160px] overflow-y-auto p-3">
              {record.text}
            </pre>

            {record.sources_cited && record.sources_cited.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="text-[10px] text-[var(--color-text-muted)] mr-1">来源：</span>
                {record.sources_cited.map((s) => (
                  <span
                    key={s}
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[var(--color-primary)]/15 text-[var(--color-primary)]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 4 维度概览 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 border-t border-[var(--color-border)] pt-3">
          {DIM_KEYS.map((d) => {
            const score =
              d.key === 'gex'
                ? record.scoring.gex_score
                : d.key === 'vix'
                  ? record.scoring.vix_score
                  : d.key === 'crypto'
                    ? record.scoring.crypto_score
                    : record.scoring.darkpool_score;
            return (
              <div key={d.key} className="flex items-center gap-2">
                <span className="text-lg opacity-80" aria-hidden>{d.icon}</span>
                <div>
                  <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">{d.label}</div>
                  <div className="msr-number text-sm">{fmtNum(score, 2)}</div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
