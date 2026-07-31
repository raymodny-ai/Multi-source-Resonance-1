/**
 * Configuration API
 * 与 backend/api/routes/config.py 对齐：
 * - GET /api/config      → { configs: ConfigItem[], count }（KV 列表）
 * - PUT /api/config      → 接受 { key, value, description } 单条更新；→ { ok, key, value }
 * - GET /api/config/defaults — 默认值列表
 * - GET /api/config/sources — 数据源启用信息 list
 * - GET /api/config/weights — Bayesian 权重
 * - POST /api/config/restore — 恢复默认
 * - POST /api/config/weights/reset — 重置权重
 */
import { get, post, put } from './client';
import type { ConfigItem, ConfigResponse } from './types';

/**
 * 原始 KV 列表（系统所有 config 条目）
 */
export function getConfig(): Promise<ConfigResponse> {
  return get<ConfigResponse>('/api/config');
}

/**
 * 更新单条 config
 * body: { key, value, description? }
 */
export function updateConfigKV(key: string, value: string, description?: string): Promise<{
  ok: boolean;
  key: string;
  value: string;
}> {
  return put('/api/config', { key, value, description });
}

/** 数据源配置（mock 标记 / API key 状态） */
export interface SourceConfig {
  name: string;
  enabled: boolean;
  has_api_key: boolean;
  mock_mode: boolean;
}

export function getSourcesConfig(): Promise<SourceConfig[]> {
  return get<SourceConfig[]>('/api/config/sources');
}

/** 更新单个数据源配置 */
export function updateSourceConfig(name: string, patch: { enabled?: boolean; api_key?: string }): Promise<{
  ok: boolean;
  source: string;
  enabled?: boolean;
}> {
  return put(`/api/config/sources/${name}`, patch);
}

/** 获取默认值 */
export function getConfigDefaults(): Promise<ConfigItem[]> {
  return get<ConfigItem[]>('/api/config/defaults');
}

/** 恢复默认配置（写入预设的 3 个 key） */
export function restoreConfigDefaults(): Promise<{ ok: boolean; message: string }> {
  return post('/api/config/restore');
}

/** Bayesian 权重状态 */
export interface WeightsInfo {
  weights: Record<string, number>;
  default_weights: Record<string, number>;
  raw_max: number;
  is_adapted: boolean;
  adapter_stats: Record<string, unknown> | null;
  posterior_summary: Record<string, unknown> | null;
}

export function getWeights(): Promise<WeightsInfo> {
  return get<WeightsInfo>('/api/config/weights');
}

/** 重置 Bayesian 权重为默认 */
export function resetWeights(): Promise<{ ok: boolean; message: string; weights: Record<string, number> }> {
  return post('/api/config/weights/reset');
}

/** Config 变更审计日志 */
export function getConfigAuditLog(): Promise<Record<string, unknown>[]> {
  return get('/api/config/audit');
}
