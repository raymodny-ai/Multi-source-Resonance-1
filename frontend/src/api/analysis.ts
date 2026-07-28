import client from './client'

export function getAnalysisGEX() {
  return client.get('/analysis/gex')
}

export function getAnalysisVIX() {
  return client.get('/analysis/vix')
}

export function getAnalysisCrypto() {
  return client.get('/analysis/crypto')
}

export function getAnalysisDarkpool() {
  return client.get('/analysis/darkpool')
}

export function getAnalysisScoring() {
  return client.get('/analysis/scoring')
}
