/**
 * Configuration API
 */
import { get, put } from './client';

export interface ConfigKV {
  key: string;
  value: string;
  description?: string;
  updated_at: string | null;
}

export interface SystemConfig {
  alert_level_1_threshold: number;
  alert_level_2_threshold: number;
  alert_level_3_threshold: number;
  pipeline_interval_sec: number;
  notification_enabled: boolean;
  data_retention_days: number;
  raw: ConfigKV[];
}

export function getConfig(): Promise<SystemConfig> {
  return get<SystemConfig>('/api/config');
}

export function updateConfig(patch: Partial<Omit<SystemConfig, 'raw'>>): Promise<SystemConfig> {
  return put<SystemConfig>('/api/config', patch);
}