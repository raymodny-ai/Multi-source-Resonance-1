import client from './client'

export function getPrometheusMetrics() {
  return client.get('/metrics', { headers: { Accept: 'text/plain' } })
}

export function getMetricsSummary() {
  return client.get('/metrics/summary')
}
