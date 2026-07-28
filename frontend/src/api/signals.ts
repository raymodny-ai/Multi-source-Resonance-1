import client from './client'

export interface SignalAlert {
  id: number
  trigger_time: string
  total_score: number
  gex_score: number
  vix_score: number
  crypto_score: number
  darkpool_score: number
  alert_level: string
  hawkes_branching_ratio: number | null
  details: string | null
  acknowledged: boolean
}

export interface SignalHistory {
  items: SignalAlert[]
  total: number
  offset: number
  limit: number
}

export function getSignalsLatest() {
  return client.get<SignalAlert>('/signals/latest')
}

export function getSignalsCurrent() {
  return client.get<SignalAlert[]>('/signals/current')
}

export function getSignalsHistory(offset = 0, limit = 50) {
  return client.get<SignalHistory>('/signals/history', { params: { offset, limit } })
}

export function getSignalsScores(days = 90) {
  return client.get('/signals/scores', { params: { days } })
}

export function acknowledgeSignal(signalId: number) {
  return client.post(`/signals/acknowledge/${signalId}`)
}

export function getAlerts(limit = 50, level?: string) {
  return client.get<SignalAlert[]>('/signals/alerts', { params: { limit, level } })
}

export function acknowledgeAlert(alertId: number) {
  return client.post(`/signals/alerts/${alertId}/acknowledge`)
}
