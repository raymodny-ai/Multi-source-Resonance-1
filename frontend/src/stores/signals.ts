import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getSignalsCurrent, getSignalsHistory, acknowledgeSignal,
  type SignalAlert, type SignalHistory,
} from '@/api/signals'
import { getDashboardScores, type DashboardScores } from '@/api/dashboard'

export const useSignalStore = defineStore('signals', () => {
  // State
  const currentSignals = ref<SignalAlert[]>([])
  const signalHistory = ref<SignalAlert[]>([])
  const totalSignals = ref(0)
  const latestScores = ref<DashboardScores | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasActiveSignals = computed(() => currentSignals.value.length > 0)
  const latestSignal = computed(() => currentSignals.value[0] ?? null)
  const level3Signals = computed(() =>
    signalHistory.value.filter((s) => s.alert_level === 'LEVEL_3')
  )

  // Actions
  async function fetchCurrentSignals() {
    try {
      const resp = await getSignalsCurrent()
      currentSignals.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchSignalHistory(offset = 0, limit = 50) {
    loading.value = true
    try {
      const resp = await getSignalsHistory(offset, limit)
      signalHistory.value = resp.data.items
      totalSignals.value = resp.data.total
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchLatestScores() {
    try {
      const resp = await getDashboardScores()
      latestScores.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function acknowledge(id: number) {
    try {
      await acknowledgeSignal(id)
      currentSignals.value = currentSignals.value.filter((s) => s.id !== id)
    } catch (e: any) {
      error.value = e.message
    }
  }

  return {
    currentSignals, signalHistory, totalSignals, latestScores,
    loading, error, hasActiveSignals, latestSignal, level3Signals,
    fetchCurrentSignals, fetchSignalHistory, fetchLatestScores, acknowledge,
  }
})
