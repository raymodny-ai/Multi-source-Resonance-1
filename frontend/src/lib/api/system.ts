/**
 * System API
 * 与 backend/api/routes/system.py 对齐：
 * - GET /api/system/status     → SystemStatusInfo（CPU/MEM/DB 等）
 * - GET /api/system/source-status → SourceStatus[]（注意是 list，不是 { sources: [...] }）
 * - GET /api/system/collection-detail → CollectionReport
 * - POST /api/system/collect-manual → CollectionReport
 */
import { get, post, put } from './client';
import type { CollectionReport, SourceStatus, SystemStatusInfo } from './types';

/** /api/system/status — CPU/MEM/DB 信息（dict） */
export function getSystemStatusInfo(): Promise<SystemStatusInfo> {
  return get<SystemStatusInfo>('/api/system/status');
}

/** /api/system/source-status — 数据源状态（list） */
export function getSourceStatusList(): Promise<SourceStatus[]> {
  return get<SourceStatus[]>('/api/system/source-status');
}

/** /api/system/collection-detail — 上一个 pipeline cycle 的 per-source 报告 */
export function getCollectionDetail(): Promise<CollectionReport> {
  return get<CollectionReport>('/api/system/collection-detail');
}

/** /api/system/collect-manual — 手动触发全量 collection（需要 JWT） */
export function triggerManualCollection(): Promise<{
  ok: boolean;
  collected_at: string | null;
  total_elapsed_sec: number;
  success_count: number;
  error_count: number;
  mock_count: number;
  sources: CollectionReport['sources'];
  write_results: Record<string, unknown>;
}> {
  return post('/api/system/collect-manual');
}

/** /api/system/auto-polling — 自动轮询状态 */
export function getAutoPollingState(): Promise<{
  enabled: boolean;
  interval_seconds: number;
}> {
  return get('/api/system/auto-polling');
}

/** PUT /api/system/auto-polling — 设置自动轮询开关 */
export function setAutoPollingState(enabled: boolean): Promise<{
  enabled: boolean;
  message: string;
}> {
  return put('/api/system/auto-polling', { enabled });
}

/** /api/system/logs — 最近日志（in-memory buffer） */
export function getSystemLogs(limit = 50): Promise<{
  timestamp: string;
  level: string;
  source: string;
  message: string;
}[]> {
  return get('/api/system/logs', { params: { limit } });
}
