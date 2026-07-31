/**
 * Analysis 页面 — LLM 增强的多源分析
 * PRD §4.7
 *
 * 后端实际：
 * - /api/analysis/scoring → 总分 + 4 维分数
 * - /api/analysis/{gex,vix,crypto,darkpool} → 每个维度的派生布尔特征
 *
 * 前端：
 * - getAnalysisLatest() 在 analysis.ts 中通过 Promise.allSettled 合并 5 端点
 * - text 由前端基于多维信号合成
 */
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { AnalysisLatestCard } from '@/components/analysis/AnalysisLatestCard';
import { AnalysisDimensionCard } from '@/components/analysis/AnalysisDimensionCard';
import { useAnalysisLatest } from '@/lib/hooks/useAnalysis';
import { useUIStore } from '@/lib/stores/ui';

export function AnalysisView() {
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);
  const [debugOpen, setDebugOpen] = useState(false);
  const { data, isLoading, error, dataUpdatedAt, refetch } = useAnalysisLatest();

  const handleRefresh = () => {
    refetch();
    setLastUpdateAt(new Date().toISOString());
  };

  return (
    <>
      <PageHeader
        title="Analysis"
        description="LLM 增强的多源分析 · 综合分数 + 4 维特征"
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDebugOpen((v) => !v)}
              aria-expanded={debugOpen}
              aria-controls="analysis-debug"
            >
              {debugOpen ? '隐藏' : '显示'} 原始 JSON
            </Button>
            <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
              刷新
            </Button>
          </>
        }
      />

      {error && (
        <AlertBanner tone="danger" title="Analysis 数据加载失败">
          {(error as Error).message}
        </AlertBanner>
      )}

      <div className="mt-4">
        <AnalysisLatestCard record={data ?? null} loading={isLoading && !data} />
      </div>

      {/* 子维度 4 卡 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <AnalysisDimensionCard
          title="GEX 维度"
          icon="Γ"
          view={data?.gex ?? null}
          loading={isLoading && !data}
        />
        <AnalysisDimensionCard
          title="VIX 维度"
          icon="σ"
          view={data?.vix ?? null}
          loading={isLoading && !data}
        />
        <AnalysisDimensionCard
          title="Crypto 维度"
          icon="₿"
          view={data?.crypto ?? null}
          loading={isLoading && !data}
        />
        <AnalysisDimensionCard
          title="Darkpool 维度"
          icon="◐"
          view={data?.darkpool ?? null}
          loading={isLoading && !data}
        />
      </div>

      {/* Debug fold */}
      {debugOpen && (
        <div id="analysis-debug" className="mt-4">
          <pre className="msr-card p-3 text-[11px] font-mono overflow-x-auto max-h-[400px]">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        综合模型：<span className="text-[var(--color-primary)]">{data?.model ?? '—'}</span> ·
        cached={String(data?.cached ?? false)} ·
        verification_score={data?.verification_score ?? '—'} ·
        上次更新：{dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}
