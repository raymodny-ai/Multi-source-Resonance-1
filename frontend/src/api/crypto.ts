import client from './client'

export interface CryptoData {
  timestamp: string
  btc_funding_rate: number
  btc_oi: number
  oi_change_1h: number
  liquidation_spike: boolean
  cryptoquant_elr: number
  funding_anomaly: boolean
  oi_crash: boolean
  leverage_cleanup: boolean
}

export function getCryptoLatest() {
  return client.get<CryptoData>('/crypto/latest')
}

export function getCryptoHistory(days = 30) {
  return client.get<CryptoData[]>('/crypto/history', { params: { days } })
}
