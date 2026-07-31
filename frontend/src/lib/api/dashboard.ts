/**
 * Dashboard API
 */
import { get } from './client';
import type { DashboardData, Signal } from './types';

export function getDashboard(): Promise<DashboardData> {
  return get<DashboardData>('/api/dashboard');
}

export function getLatestSignal(): Promise<Signal | null> {
  return get<Signal | null>('/api/signals/latest');
}

export function getDataQuality(): Promise<{
  sources_online: number;
  sources_total: number;
  mock_sources: string[];
  last_cycle_at: string | null;
}> {
  return get('/api/dashboard/data-quality');
}