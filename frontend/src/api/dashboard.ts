import client from './client'

export interface DashboardMeta {
  mock_sources: string[]
}

export interface DashboardData {
  fetched_at: string
  gex: Record<string, any> | null
  vix: Record<string, any> | null
  crypto: Record<string, any> | null
  darkpool: Record<string, any> | null
  signal: Record<string, any> | null
  _meta?: DashboardMeta | null
}

export interface DashboardScores {
  total_score: number
  gex_score: number
  vix_score: number
  crypto_score: number
  darkpool_score: number
  alert_level: string
  trigger_time?: string
}

export interface ResonanceHistoryItem {
  trigger_time: string
  total_score: number
  gex_score: number
  vix_score: number
  crypto_score: number
  darkpool_score: number
  alert_level: string
}

export function getDashboard() {
  return client.get<DashboardData>('/dashboard')
}

export function getDashboardScores() {
  return client.get<DashboardScores>('/dashboard/scores')
}

export function getRecentAlerts(limit = 10) {
  return client.get('/dashboard/recent-alerts', { params: { limit } })
}

export function getResonanceHistory(days = 90) {
  return client.get<ResonanceHistoryItem[]>('/dashboard/resonance-history', { params: { days } })
}

export function getCrossAssetHeatmap() {
  return client.get('/dashboard/cross-asset-heatmap')
}

export function getGEXCurve(days = 90) {
  return client.get('/dashboard/gex-curve', { params: { days } })
}

export function getMultiChannelCurve(days = 90) {
  return client.get('/dashboard/multi-channel-curve', { params: { days } })
}

export function getDataQuality() {
  return client.get('/dashboard/data-quality')
}

export function getPipelineMetrics() {
  return client.get('/dashboard/pipeline-metrics')
}
