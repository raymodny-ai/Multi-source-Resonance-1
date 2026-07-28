import client from './client'

export interface VIXData {
  timestamp: string
  vix_spot: number
  vx1: number
  vx2: number
  term_structure_ratio: number
  term_structure_state: string
  panic_premium: number
}

export function getVIXLatest() {
  return client.get<VIXData>('/vix/latest')
}

export function getVIXTermStructure() {
  return client.get<VIXData>('/vix/term-structure')
}

export function getVIXHistory(days = 90) {
  return client.get<VIXData[]>('/vix/history', { params: { days } })
}
