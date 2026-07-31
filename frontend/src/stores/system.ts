import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getSystemStatus, getSourceStatus, getSystemLogs,
  getAutoPolling, setAutoPolling, triggerManualCollection,
  getCollectionDetail,
  type SystemStatus, type SourceStatus, type AutoPollingState,
  type CollectionReport, type CollectionSourceDetail, type CollectionDetailResponse,
} from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  // State
  const systemStatus = ref<SystemStatus | null>(null)
  const sourceStatuses = ref<SourceStatus[]>([])
  const systemLogs = ref<Record<string, any>[]>([])
  const autoPolling = ref<AutoPollingState | null>(null)
  const collectionDetail = ref<CollectionDetailResponse | null>(null)
  const lastCollection = ref<CollectionReport | null>(null)
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
  const mockSources = computed(() =>
    sourceStatuses.value.filter((s) => s.is_mock)
  )
  const sourceErrors = computed(() =>
    sourceStatuses.value.filter((s) => !!s.last_error)
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
    loading.value = true
    error.value = null
    try {
      const resp = await getSystemStatus()
      systemStatus.value = resp.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSourceStatus() {
    loading.value = true
    error.value = null
    try {
      const resp = await getSourceStatus()
      sourceStatuses.value = resp.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCollectionDetail() {
    try {
      const resp = await getCollectionDetail()
      collectionDetail.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchLogs(limit = 50) {
    error.value = null
    try {
      const resp = await getSystemLogs(limit)
      systemLogs.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchAutoPolling() {
    error.value = null
    try {
      const resp = await getAutoPolling()
      autoPolling.value = resp.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function toggleAutoPolling(enabled: boolean) {
    error.value = null
    try {
      await setAutoPolling(enabled)
      if (autoPolling.value) autoPolling.value.enabled = enabled
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function collectManual() {
    collecting.value = true
    error.value = null
    try {
      const resp = await triggerManualCollection()
      lastCollection.value = resp.data
      // After collection, refresh source status + collection detail so the
      // UI can show the new is_mock / error state for each source.
      await fetchSourceStatus()
      await fetchCollectionDetail()
    } catch (e: any) {
      error.value = e.message
    } finally {
      collecting.value = false
    }
  }

  return {
    systemStatus, sourceStatuses, systemLogs, autoPolling,
    collectionDetail, lastCollection,
    loading, collecting, error,
    onlineSources, offlineSources, mockSources, sourceErrors, uptimeFormatted,
    fetchSystemStatus, fetchSourceStatus, fetchLogs,
    fetchAutoPolling, toggleAutoPolling, collectManual, fetchCollectionDetail,
  }
})

