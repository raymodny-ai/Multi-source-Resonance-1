import { defineStore } from 'pinia'
import { ref, computed, onScopeDispose } from 'vue'
import { getDashboard, getDashboardScores, type DashboardScores, type DashboardData } from '@/api/dashboard'
import { getGEXSummary, type GEXSnapshot } from '@/api/gex'
import { getVIXLatest, type VIXData } from '@/api/vix'
import { getCryptoLatest, type CryptoData } from '@/api/crypto'
import { getDarkpoolLatest, type DarkpoolData } from '@/api/darkpool'
import wsClient from '@/api/websocket'

export interface DimensionError {
  dimension: string
  message: string
  timestamp: string
}

export interface MockSourceRef {
  source: string
  mock_reason?: string | null
  retry_count?: number
  last_seen: string
}

export const useMarketStore = defineStore('market', () => {
  // State
  const dashboardData = ref<DashboardData | null>(null)
  const scores = ref<DashboardScores | null>(null)
  const gexSummary = ref<GEXSnapshot[]>([])
  const vixData = ref<VIXData | null>(null)
  const cryptoData = ref<CryptoData | null>(null)
  const darkpoolData = ref<DarkpoolData | null>(null)
  const loading = ref(false)
  const lastUpdated = ref<string | null>(null)
  const error = ref<string | null>(null)
  // ponytail: track per-dimension fetch failures and per-source mock usage so
  // the UI can show targeted toasts / banners without relying on global state.
  const dimensionErrors = ref<Record<string, DimensionError>>({})
  const mockSources = ref<Record<string, MockSourceRef>>({})

  // Getters
  const alertLevel = computed(() => scores.value?.alert_level ?? 'NONE')
  const totalScore = computed(() => scores.value?.total_score ?? 0)
  const dimensionScores = computed(() => ({
    gex: scores.value?.gex_score ?? 0,
    vix: scores.value?.vix_score ?? 0,
    crypto: scores.value?.crypto_score ?? 0,
    darkpool: scores.value?.darkpool_score ?? 0,
  }))
  const hasMockData = computed(() => Object.keys(mockSources.value).length > 0)

  const recordDimensionError = (dimension: string, message: string) => {
    dimensionErrors.value = {
      ...dimensionErrors.value,
      [dimension]: {
        dimension,
        message,
        timestamp: new Date().toISOString(),
      },
    }
  }

  const recordMockSource = (source: string, info: { mock_reason?: string | null; retry_count?: number }) => {
    const now = new Date().toISOString()
    const previous = mockSources.value[source]
    mockSources.value = {
      ...mockSources.value,
      [source]: {
        source,
        mock_reason: info.mock_reason ?? previous?.mock_reason ?? null,
        retry_count: info.retry_count ?? previous?.retry_count ?? 0,
        last_seen: now,
      },
    }
  }

  // ponytail: automatically clear stale errors so the banner resets when a
  // subsequent fetch succeeds.
  const clearDimensionError = (dimension: string) => {
    if (dimensionErrors.value[dimension]) {
      const next = { ...dimensionErrors.value }
      delete next[dimension]
      dimensionErrors.value = next
    }
  }

  // Actions
  async function fetchDashboard() {
    loading.value = true
    error.value = null
    try {
      const [dashResp, scoresResp] = await Promise.all([
        getDashboard(),
        getDashboardScores(),
      ])
      dashboardData.value = dashResp.data
      scores.value = scoresResp.data
      lastUpdated.value = new Date().toISOString()

      // Consume backend-reported mock sources so the banner reflects the latest DB state.
      const meta = dashResp.data?._meta
      if (meta?.mock_sources?.length) {
        for (const src of meta.mock_sources) {
          recordMockSource(src, {})
        }
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch dashboard'
    } finally {
      loading.value = false
    }
  }

  async function fetchAllDimensions() {
    const dims = [
      { key: 'gex', fn: getGEXSummary, fallback: { data: [] as GEXSnapshot[] } },
      { key: 'vix', fn: getVIXLatest, fallback: { data: null as VIXData | null } },
      { key: 'crypto', fn: getCryptoLatest, fallback: { data: null as CryptoData | null } },
      { key: 'darkpool', fn: getDarkpoolLatest, fallback: { data: null as DarkpoolData | null } },
    ]
    const results = await Promise.all(
      dims.map(async (d) => {
        try {
          const resp = await d.fn()
          return { key: d.key, resp, error: null as string | null }
        } catch (e: any) {
          return { key: d.key, resp: null, error: e?.message || 'fetch failed' }
        }
      }),
    )
    for (const r of results) {
      if (r.error) {
        recordDimensionError(r.key, r.error)
      } else {
        clearDimensionError(r.key)
      }
    }
    const find = (k: string) => results.find((r) => r.key === k)
    gexSummary.value = (find('gex')?.resp?.data ?? []) as GEXSnapshot[]
    vixData.value = (find('vix')?.resp?.data ?? null) as VIXData | null
    cryptoData.value = (find('crypto')?.resp?.data ?? null) as CryptoData | null
    darkpoolData.value = (find('darkpool')?.resp?.data ?? null) as DarkpoolData | null
  }

  // ponytail: WebSocket live-update — backend broadcasts `data.fetch.complete`
  // after each periodic pipeline run (~30s). We re-fetch dashboard + dimensions
  // on that signal so the UI follows DB state without manual refresh.
  const liveHandler = (msg: { topic: string; payload: any; level?: string }) => {
    if (msg.topic === 'data.fetch.complete') {
      // fire-and-forget; fetchDashboard/fetchAllDimensions handle their own errors
      void fetchDashboard()
      void fetchAllDimensions()
    } else if (msg.topic === 'data.mock.fallback') {
      const src = msg.payload?.source
      if (src) {
        recordMockSource(src, {
          mock_reason: msg.payload?.mock_reason ?? null,
          retry_count: msg.payload?.retry_count ?? 0,
        })
      }
    } else if (msg.topic === 'pipeline.cycle.complete') {
      // Periodic cycle finished — treat as a soft heartbeat that clears stale errors.
      // Individual fetchers will repopulate dimensionErrors if they still fail.
      void fetchAllDimensions()
    }
  }
  wsClient.subscribe('*', liveHandler)
  onScopeDispose(() => wsClient.unsubscribe('*', liveHandler))

  return {
    dashboardData, scores, gexSummary, vixData, cryptoData, darkpoolData,
    loading, lastUpdated, error, alertLevel, totalScore, dimensionScores,
    dimensionErrors, mockSources, hasMockData,
    fetchDashboard, fetchAllDimensions,
  }
})

