/**
 * LLM-Enhanced Analysis API
 * 与 backend/api/routes/analysis.py 对齐：
 * 后端没有 /api/analysis/latest 或 /api/analysis/generate。
 * 实际端点是 /api/analysis/{gex,vix,crypto,darkpool,scoring} 5 个分析视图
 *
 * 为 PRD §4.7 的「Latest Analysis Card」+「Request Analysis」按钮设计以下前端 API：
 * - getAnalysisLatest()：合并 4 个维度 + scoring，最新一条
 * - generateAnalysis()：触发后端 mock（没有生成端点，UI 上以 toast 提示）
 * - getAnalysisHistory()：暂无后端支持，返回空数组
 *
 * 注：根据 PRD「LLM 走 WebSocket」决策（Open Question 3），generate 实际上通过
 * ws ANALYSIS_COMPLETE 推送。当前端不再暴露单独 generate 按钮（保持 UI 与 P1 一致），
 * 但保留函数以防用户开启时支持。
 */
import { get } from './client';

/** scoring 综合视图 */
export interface AnalysisScoring {
  trigger_time: string | null;
  total_score: number | null;
  gex_score: number | null;
  vix_score: number | null;
  crypto_score: number | null;
  darkpool_score: number | null;
  alert_level: string | null;
  hawkes_branching_ratio: number | null;
  acknowledged: boolean | null;
  max_score: number;
  level_thresholds: {
    LEVEL_1: number;
    LEVEL_2: number;
    LEVEL_3: number;
  };
}

/** 单维度分析视图（带 analysis 子对象） */
export interface AnalysisDimensionView {
  timestamp?: string;
  date?: string;
  /** 派生布尔字段集合（见 backend 路由 logic） */
  analysis?: Record<string, boolean>;
  /** 任意其他字段（snapshot, strike_stats 等） */
  [key: string]: unknown;
}

/**
 * API 错误消息形状（后端在没有数据时返回 { message: ... }） */
interface ApiMessage {
  message: string;
}

/** 综合 analysis 聚合视图（前端归一化） */
export interface AnalysisRecord {
  fetched_at: string;
  scoring: AnalysisScoring;
  gex: AnalysisDimensionView | null;
  vix: AnalysisDimensionView | null;
  crypto: AnalysisDimensionView | null;
  darkpool: AnalysisDimensionView | null;
  /** 来自 PRD §4.7「置信度」字段——暂用 scoring.level_thresholds 的反向归一化 */
  confidence: number;
  /** 是否缓存命中：P1 P2 都返回 mock 模式：false */
  cached: boolean;
  model: string;
  /** LLM "analysis text" - P1 P2 阶段由前端基于多维信号生成 */
  text: string;
  sources_cited: string[];
  verification_score: number | null;
}

function unwrap<T>(r: PromiseSettledResult<T | ApiMessage | null>): T | null {
  if (r.status !== 'fulfilled') return null;
  const v = r.value;
  if (v === null || v === undefined) return null;
  if (typeof v === 'object' && 'message' in v && Object.keys(v).length === 1) {
    return null;
  }
  return v as T;
}

/**
 * 拉取全部 4 个维度 + scoring 综合
 * 任何端点失败都不会抛错，退化到 null / 默认 score
 */
export async function getAnalysisLatest(): Promise<AnalysisRecord | null> {
  const settled = await Promise.allSettled([
    get<AnalysisScoring | ApiMessage>('/api/analysis/scoring'),
    get<AnalysisDimensionView | ApiMessage>('/api/analysis/gex'),
    get<AnalysisDimensionView | ApiMessage>('/api/analysis/vix'),
    get<AnalysisDimensionView | ApiMessage>('/api/analysis/crypto'),
    get<AnalysisDimensionView | ApiMessage>('/api/analysis/darkpool'),
  ]);
  const [scoringR, gexR, vixR, cryptoR, dpR] = settled;
  if (scoringR.status === 'rejected') return null;
  const scoring = unwrap<AnalysisScoring>(scoringR as PromiseSettledResult<AnalysisScoring | ApiMessage>);
  if (!scoring) return null;

  const gex = unwrap<AnalysisDimensionView>(
    gexR as PromiseSettledResult<AnalysisDimensionView | ApiMessage | null>
  );
  const vix = unwrap<AnalysisDimensionView>(
    vixR as PromiseSettledResult<AnalysisDimensionView | ApiMessage | null>
  );
  const crypto = unwrap<AnalysisDimensionView>(
    cryptoR as PromiseSettledResult<AnalysisDimensionView | ApiMessage | null>
  );
  const darkpool = unwrap<AnalysisDimensionView>(
    dpR as PromiseSettledResult<AnalysisDimensionView | ApiMessage | null>
  );

  const total = scoring.total_score ?? 0;
  const max = scoring.max_score ?? 5.0;
  const confidence = max > 0 ? Math.min(1, total / max) : 0;

  // 由前端合成的「analysis text」（LLM 由 Open Question 3 决定走 WS 推送，P2 阶段先用 synthesis）
  const lines: string[] = [];
  lines.push(`综合共振分数：${total.toFixed(2)} / ${max.toFixed(1)}（${scoring.alert_level ?? 'NONE'}）`);
  const dims: [string, number | null][] = [
    ['GEX', scoring.gex_score],
    ['VIX', scoring.vix_score],
    ['Crypto', scoring.crypto_score],
    ['Darkpool', scoring.darkpool_score],
  ];
  lines.push('维度分布：');
  dims.forEach(([n, s]) => lines.push(`- ${n}: ${s?.toFixed(2) ?? '—'}`));
  if (scoring.hawkes_branching_ratio != null) {
    lines.push(`Hawkes 分枝比：${scoring.hawkes_branching_ratio.toFixed(3)}（>1 表示自激）`);
  }
  return {
    fetched_at: new Date().toISOString(),
    scoring,
    gex,
    vix,
    crypto,
    darkpool,
    confidence,
    cached: false,
    model: 'heuristic-synth',
    text: lines.join('\n'),
    sources_cited: ['gex', 'vix', 'crypto', 'darkpool'],
    verification_score: null,
  };
}

/**
 * 触发分析生成（P1 P2 阶段后端未实现该端点——返回当前分析作为代替）
 * PRD Open Question 3 决策 LLM 走 WS，本函数保留兼容
 */
export async function generateAnalysis(): Promise<AnalysisRecord | null> {
  return getAnalysisLatest();
}

/**
 * 历史记录列表（P1 P2 后端未提供 history 端点，返回空数组）
 * P3 阶段会调用实际端点
 */
export async function getAnalysisHistory(_days = 30): Promise<AnalysisRecord[]> {
  return [];
}
