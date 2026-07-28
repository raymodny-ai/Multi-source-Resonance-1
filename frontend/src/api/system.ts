import client from './client'

export interface SystemStatus {
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  db_size_mb: number
  active_connections: number
  uptime_seconds: number
  python_version: string
  platform: string
}

export interface SourceStatus {
  name: string
  status: 'online' | 'degraded' | 'offline'
  method: string
  availability_pct: number
  last_data_ts: string | null
  total_rows: number | null
  age_minutes: number
}

export interface AutoPollingState {
  enabled: boolean
  interval_seconds: number
}

export function getSystemStatus() {
  return client.get<SystemStatus>('/system/status')
}

export function getSourceStatus() {
  return client.get<SourceStatus[]>('/system/source-status')
}

export function getSystemLogs(limit = 50) {
  return client.get<Record<string, any>[]>('/system/logs', { params: { limit } })
}

export function getAutoPolling() {
  return client.get<AutoPollingState>('/system/auto-polling')
}

export function setAutoPolling(enabled: boolean) {
  return client.put('/system/auto-polling', { enabled })
}

export function triggerManualCollection() {
  return client.post('/system/collect-manual')
}
