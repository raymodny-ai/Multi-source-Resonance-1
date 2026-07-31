/**
 * Metrics API（Prometheus 格式或 JSON 摘要）
 */
import { get } from './client';

export interface MetricsSummary {
  pipeline_up: number;
  signals_total: number;
  fetcher_success_rate: number;
  /** 维度命中率 */
  dimension_hit_rate: Record<string, number>;
  /** 最近 1h 信号计数 */
  signals_last_1h: number;
  fetched_at: string | null;
}

export function getMetricsSummary(): Promise<MetricsSummary> {
  return get<MetricsSummary>('/api/metrics/summary');
}