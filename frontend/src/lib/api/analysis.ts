/**
 * LLM-Enhanced Analysis API
 */
import { get, post } from './client';

export interface AnalysisRecord {
  id: number | string;
  generated_at: string;
  confidence: number;
  model: string;
  text: string;
  /** 多模型一致性（1.0 完全一致） */
  verification_score: number | null;
  /** 缓存命中信息 */
  cached: boolean;
  sources_cited: string[];
}

export function getLatestAnalysis(): Promise<AnalysisRecord | null> {
  return get<AnalysisRecord | null>('/api/analysis/latest');
}

export function generateAnalysis(): Promise<AnalysisRecord> {
  return post<AnalysisRecord>('/api/analysis/generate');
}