import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDashboard, getDashboardScores, type DashboardScores, type DashboardData } from '@/api/dashboard'
import { getGEXSummary, type GEXSnapshot } from '@/api/gex'
import { getVIXLatest, type VIXData } from '@/api/vix'
import { getCryptoLatest, type CryptoData } from '@/api/crypto'
import { getDarkpoolLatest, type DarkpoolData } from '@/api/darkpool'

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

  // Getters
  const alertLevel = computed(() => scores.value?.alert_level ?? 'NONE')
  const totalScore = computed(() => scores.value?.total_score ?? 0)
  const dimensionScores = computed(() => ({
    gex: scores.value?.gex_score ?? 0,
    vix: scores.value?.vix_score ?? 0,
    crypto: scores.value?.crypto_score ?? 0,
    darkpool: scores.value?.darkpool_score ?? 0,
  }))

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
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch dashboard'
    } finally {
      loading.value = false
    }
  }

  async function fetchAllDimensions() {
    try {
      const [gexResp, vixResp, cryptoResp, darkpoolResp] = await Promise.all([
        getGEXSummary().catch(() => ({ data: [] })),
        getVIXLatest().catch(() => ({ data: null })),
        getCryptoLatest().catch(() => ({ data: null })),
        getDarkpoolLatest().catch(() => ({ data: null })),
      ])
      gexSummary.value = gexResp.data
      vixData.value = vixResp.data
      cryptoData.value = cryptoResp.data
      darkpoolData.value = darkpoolResp.data
    } catch (e: any) {
      console.error('Failed to fetch dimensions:', e)
    }
  }

  return {
    dashboardData, scores, gexSummary, vixData, cryptoData, darkpoolData,
    loading, lastUpdated, error, alertLevel, totalScore, dimensionScores,
    fetchDashboard, fetchAllDimensions,
  }
})
