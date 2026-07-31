/**
 * System API
 */
import { get, post } from './client';
import type { CollectionReport, SystemHealth } from './types';

export function getSystemHealth(): Promise<SystemHealth> {
  return get<SystemHealth>('/api/system/health');
}

export function getSystemStatus(): Promise<SystemHealth> {
  return get<SystemHealth>('/api/system/status');
}

export function getCollectionDetail(): Promise<CollectionReport> {
  return get<CollectionReport>('/api/system/collection-detail');
}

export function triggerManualCollection(): Promise<CollectionReport> {
  return post<CollectionReport>('/api/system/collect-manual');
}

export function getMetrics(): Promise<unknown> {
  return get('/api/metrics');
}