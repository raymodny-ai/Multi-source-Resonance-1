import client from './client'

export interface GEXSnapshot {
  id: number
  symbol: string
  timestamp: string
  net_gex: number
  call_gex: number
  put_gex: number
  zero_gamma_level: number
  call_wall: number
  put_wall: number
  spot_price: number
  total_gamma: number
  quality_score: number
  oi_coverage_pct: number
}

export interface GEXStrike {
  strike: number
  call_gex: number
  put_gex: number
  call_oi: number
  put_oi: number
  call_vol: number
  put_vol: number
  net_gex: number
}

export interface GEXDashboardView {
  symbol: string
  fetched_at: string
  latest: GEXSnapshot | null
  levels: {
    call_wall: number
    put_wall: number
    zero_gamma_level: number
    spot_price: number
    net_gex: number
    call_gex: number
    put_gex: number
  } | null
  history: Record<string, any>[]
  long_history: Record<string, any>[]
  strikes: {
    timestamp: string
    spot_price: number
    strike_count: number
    strikes: GEXStrike[]
  } | null
  symbols: Record<string, any>[]
}

export function getGEXSymbols() {
  return client.get('/gex/symbols')
}

export function getGEXSummary() {
  return client.get<GEXSnapshot[]>('/gex/summary')
}

export function getGEXHistory(days = 90) {
  return client.get('/gex/history', { params: { days } })
}

export function getGEXLatest(symbol: string) {
  return client.get<GEXSnapshot>(`/gex/${symbol}/latest`)
}

export function getGEXSymbolHistory(symbol: string, days = 3) {
  return client.get(`/gex/${symbol}/history`, { params: { days } })
}

export function getGEXLevels(symbol: string) {
  return client.get(`/gex/${symbol}/levels`)
}

export function getGEXStrikes(symbol: string, limit = 200) {
  return client.get<{ strikes: GEXStrike[] }>(`/gex/${symbol}/strikes`, { params: { limit } })
}

export function getGEXDashboardView(
  symbol: string,
  params?: { history_days?: number; long_days?: number; strikes_limit?: number }
) {
  return client.get<GEXDashboardView>(`/gex/${symbol}/dashboard-view`, { params })
}
