import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getSystemStatus, getSourceStatus, getSystemLogs,
  getAutoPolling, setAutoPolling, triggerManualCollection,
  type SystemStatus, type SourceStatus, type AutoPollingState,
} from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  // State
  const systemStatus = ref<SystemStatus | null>(null)
  const sourceStatuses = ref<SourceStatus[]>([])
  const systemLogs = ref<Record<string, any>[]>([])
  const autoPolling = ref<AutoPollingState | null>(null)
  const loading = ref(false)
  const collecting = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const onlineSources = computed(() =>
    sourceStatuses.value.filter((s) => s.status === 'online')
  )
  const offlineSources = computed(() =>
    sourceStatuses.value.filter((s) => s.status === 'offline')
  )
  const uptimeFormatted = computed(() => {
    if (!systemStatus.value) return '—'
    const secs = systemStatus.value.uptime_seconds
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    return `${h}h ${m}m`
  })

  // Actions
  async function fetchSystemStatus() {
    try {
      const resp = await getSystemStatus()
      systemStatus.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchSourceStatus() {
    try {
      const resp = await getSourceStatus()
      sourceStatuses.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchLogs(limit = 50) {
    try {
      const resp = await getSystemLogs(limit)
      systemLogs.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchAutoPolling() {
    try {
      const resp = await getAutoPolling()
      autoPolling.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function toggleAutoPolling(enabled: boolean) {
    try {
      await setAutoPolling(enabled)
      if (autoPolling.value) autoPolling.value.enabled = enabled
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function collectManual() {
    collecting.value = true
    try {
      await triggerManualCollection()
      await fetchSourceStatus()
    } catch (e: any) {
      error.value = e.message
    } finally {
      collecting.value = false
    }
  }

  return {
    systemStatus, sourceStatuses, systemLogs, autoPolling,
    loading, collecting, error,
    onlineSources, offlineSources, uptimeFormatted,
    fetchSystemStatus, fetchSourceStatus, fetchLogs,
    fetchAutoPolling, toggleAutoPolling, collectManual,
  }
})
