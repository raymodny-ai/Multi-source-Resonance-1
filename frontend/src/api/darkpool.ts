import client from './client'

export interface DarkpoolData {
  date: string
  dix_value: number
  chartexchange_short_ratio: number
  stockgrid_20d_slope: number
  stockgrid_60d_slope: number
  stockgrid_divergence: boolean
  dbmf_ma5_recovery: boolean
  aggregated_signal: boolean
  v_net: number
  ema_fast_5: number
  ema_slow_20: number
  zero_cross_signal: string | null
  momentum_reversal_signal: string | null
}

export interface DarkpoolFlow {
  date: string
  dix_value: number
  v_net: number
  ema_fast_5: number
  ema_slow_20: number
  aggregated_signal: boolean
  zero_cross_signal: string | null
  momentum_reversal_signal: string | null
}

export interface DarkpoolHistoryIntradayRow {
  date: string
  timestamp: string
  dix_value: number | null
  gex_value: number | null
  spx_price: number | null
  chartexchange_short_ratio: number | null
  source: string | null
}

export function getDarkpoolLatest() {
  return client.get<DarkpoolData>('/darkpool/latest')
}

export function getDarkpoolFlow(days = 30) {
  return client.get<DarkpoolFlow[]>('/darkpool/flow', { params: { days } })
}

export function getDarkpoolHistory(days = 90) {
  return client.get<DarkpoolData[]>('/darkpool/history', { params: { days } })
}

export function getDarkpoolHistoryIntraday(days = 90) {
  return client.get<DarkpoolHistoryIntradayRow[]>(
    '/darkpool/history-intraday',
    { params: { days } },
  )
}