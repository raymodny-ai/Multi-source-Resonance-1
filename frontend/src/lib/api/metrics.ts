/**
 * Metrics API
 * 与 backend/api/routes/metrics.py 对齐：
 * - GET /api/metrics         → Prometheus 文本格式（不要在类型化 JSON 用）
 * - GET /api/metrics/summary → JSON summary { uptime_seconds, pipeline, event_bus, database }
 */
import { get } from './client';
import type { MetricsSummary } from './types';

export type { MetricsSummary };

export function getMetricsSummary(): Promise<MetricsSummary> {
  return get<MetricsSummary>('/api/metrics/summary');
}

/** Prometheus 文本指标 — 用于嵌入式展示 */
export function getPrometheusMetrics(): Promise<string> {
  return get<string>('/api/metrics', { responseType: 'text' });
}
