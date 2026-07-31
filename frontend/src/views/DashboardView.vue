<template>
  <div class="dashboard-view">
    <!-- Global banners: mock data + WS + dimension errors -->
    <MockDataBanner
      v-if="mockBannerVisible"
      :sources="mockBannerSources"
      title="当前数据源包含模拟值"
      :dismissible="true"
      @update:model-value="mockBannerVisible = $event"
    />

    <div v-if="hasDimensionErrors" class="error-banner" role="alert">
      <span class="error-banner-icon">❗</span>
      <div class="error-banner-text">
        <strong>部分维度获取失败</strong>
        <span class="error-banner-detail">
          {{ dimensionErrorSummary }}
        </span>
      </div>
      <button class="error-banner-close" @click="clearDimensionErrors" type="button">
        ×
      </button>
    </div>

    <div v-if="!wsConnected" class="ws-warning-banner" role="status">
      <span class="ws-warning-icon">⚠</span>
      <div class="ws-warning-text">
        <strong>实时连接已断开</strong>
        <span class="ws-warning-detail">正在尝试重连，数据展示可能不完整</span>
      </div>
    </div>

    <!-- DEBUG: 临时浮动面板 — 手动触发 fetchDashboard + 显示 ws 状态 -->
    <div class="msr-debug-panel">
      <button class="msr-debug-btn" @click="manualRefresh" :disabled="refreshing">
        {{ refreshing ? '⟳ 拉取中...' : '🔄 手动刷新数据' }}
      </button>
      <div class="msr-debug-status">
        <div>WS: {{ wsStateLabel }}</div>
        <div>Cycle: {{ pipelineCycle }}</div>
        <div>Last fetch: {{ lastFetchAgo }}</div>
        <div>GEX ts: {{ gexTimestamp }}</div>
      </div>
      <button class="msr-debug-btn-sm" @click="toggleDebugLog">
        {{ showDebugLog ? '隐藏' : '显示' }} 调试日志
      </button>
      <pre v-if="showDebugLog" class="msr-debug-log">{{ debugLogText }}</pre>
    </div>

    <div class="dashboard-grid">
      <!-- Score Overview -->
      <div class="grid-score">
        <ScoreOverview
          :total-score="marketStore.totalScore"
          :alert-level="marketStore.alertLevel"
          :dimensions="marketStore.dimensionScores"
        />
      </div>

      <!-- Radar Chart -->
      <div class="grid-radar glass-card">
        <h3 class="section-title">四维雷达</h3>
        <RadarChart :dimensions="marketStore.dimensionScores" :height="260" />
      </div>

      <!-- Gauge -->
      <div class="grid-gauge glass-card">
        <h3 class="section-title">信号强度</h3>
        <GaugeChart :value="marketStore.totalScore" :max="5.0" title="Resonance" :height="260" />
      </div>

      <!-- Signal Card -->
      <div class="grid-signal">
        <SignalCard :signal="signalStore.latestSignal" />
      </div>

      <!-- Signal Timeline -->
      <div class="grid-timeline glass-card">
        <h3 class="section-title">信号时间线</h3>
        <SignalTimeline :signals="signalStore.signalHistory.slice(0, 10)" />
      </div>

      <!-- Data Summary Cards -->
      <div class="grid-summary glass-card">
        <h3 class="section-title">数据摘要</h3>
        <div class="summary-cards">
          <div class="summary-item">
            <span class="summary-label">GEX Net</span>
            <span class="summary-value" :class="gexClass">{{ formatGEX(gexNet) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">VIX Spot</span>
            <span
              class="summary-value"
              :class="valueClass(marketStore.vixData?.vix_spot)"
            >{{ marketStore.vixData?.vix_spot?.toFixed(2) ?? '—' }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">BTC Funding</span>
            <span
              class="summary-value"
              :class="valueClass(marketStore.cryptoData?.btc_funding_rate)"
            >{{ formatFunding(marketStore.cryptoData?.btc_funding_rate) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">DIX Value</span>
            <span
              class="summary-value"
              :class="valueClass(marketStore.darkpoolData?.dix_value)"
            >{{ marketStore.darkpoolData?.dix_value?.toFixed(2) ?? '—' }}</span>
          </div>
        </div>
      </div>

      <!-- Source Status -->
      <div class="grid-sources glass-card">
        <h3 class="section-title">数据源状态</h3>
        <div class="source-grid">
          <SourceStatusCard v-for="src in systemStore.sourceStatuses" :key="src.name" :source="src" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, watch } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useSignalStore } from '@/stores/signals'
import { useSystemStore } from '@/stores/system'
import wsClient from '@/api/websocket'
import ScoreOverview from '@/components/dashboard/ScoreOverview.vue'
import SignalCard from '@/components/dashboard/SignalCard.vue'
import SourceStatusCard from '@/components/dashboard/SourceStatusCard.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import RadarChart from '@/components/charts/RadarChart.vue'
import GaugeChart from '@/components/charts/GaugeChart.vue'
import SignalTimeline from '@/components/signals/SignalTimeline.vue'

const marketStore = useMarketStore()
const signalStore = useSignalStore()
const systemStore = useSystemStore()

const gexNet = computed(() => marketStore.dashboardData?.gex?.net_gex)
const gexClass = computed(() => (gexNet.value && gexNet.value > 0) ? 'text-green' : 'text-red')

// Banner visibility: combined mock-source state.
const mockBannerVisible = ref(true)
const mockBannerSources = computed(() => Object.values(marketStore.mockSources).map((m) => m.source))
// Hide banner if no mock sources are currently reported.
const showMockBanner = computed(() => mockBannerSources.value.length > 0)

// Per-dimension fetch failure surfacing.
const hasDimensionErrors = computed(() => Object.keys(marketStore.dimensionErrors).length > 0)
const dimensionErrorSummary = computed(() =>
  Object.values(marketStore.dimensionErrors)
    .map((d) => `${d.dimension.toUpperCase()}: ${d.message}`)
    .join('；'),
)
function clearDimensionErrors() {
  marketStore.dimensionErrors = {}
}

// WS connection state — use the new wsClient.isConnected getter instead of poking `ws`.
const wsConnected = computed(() => wsClient.isConnected)

// ─── DEBUG: 手动刷新 + 状态显示 ──────────────────────────────
const refreshing = ref(false)
const showDebugLog = ref(false)
const debugLogText = ref('')
const wsState = ref('?')
const pipelineCycle = ref('?')
const lastFetchAgo = ref('?')
const gexTimestamp = ref('?')
let pollTimer: ReturnType<typeof setInterval> | null = null
let debugWsStateHandler: ((s: { connected: boolean }) => void) | null = null

const wsStateLabel = computed(() => {
  if (wsConnected.value) return 'OPEN'
  return wsState.value
})

function toggleDebugLog() {
  showDebugLog.value = !showDebugLog.value
  if (showDebugLog.value) {
    try {
      const lines = JSON.parse(localStorage.getItem('msr_debug_ws') || '[]') as string[]
      debugLogText.value = lines.join('\n') || '(空)'
    } catch { debugLogText.value = '(localStorage 不可用)' }
  }
}

async function manualRefresh() {
  refreshing.value = true
  try {
    await Promise.all([
      marketStore.fetchDashboard(),
      marketStore.fetchAllDimensions(),
      signalStore.fetchCurrentSignals(),
      signalStore.fetchSignalHistory(),
      systemStore.fetchSourceStatus(),
    ])
    ;(window as any).__msrDebugLog?.('manualRefresh OK')
  } catch (e) {
    ;(window as any).__msrDebugLog?.('manualRefresh FAIL', String(e))
  } finally {
    refreshing.value = false
    pollStatus()
  }
}

async function pollStatus() {
  // ws state — use the public getter instead of poking readyState.
  wsState.value = wsClient.connectionState
  // pipeline cycle + last fetch ago
  try {
    const r = await fetch('/api/system/pipeline-status')
    const j = await r.json()
    pipelineCycle.value = `count=${j.pipeline.cycle_count}`
    if (j.pipeline.last_report?.cycle_ts) {
      const age = Math.round((Date.now() - new Date(j.pipeline.last_report.cycle_ts).getTime()) / 1000)
      lastFetchAgo.value = `${age}s ago (cycle ${j.pipeline.last_report.cycle_number})`
    } else {
      lastFetchAgo.value = '—'
    }
  } catch (e) {
    pipelineCycle.value = 'fetch err'
  }
  // gex ts
  const gd = marketStore.dashboardData as any
  gexTimestamp.value = gd?.gex?.timestamp ?? 'null'
}

function valueClass(v: number | null | undefined): string {
  // Distinguish "no data" (null/undefined) from "fetch failed" via store.
  if (v == null) {
    return Object.keys(marketStore.dimensionErrors).length ? 'value-error' : ''
  }
  return ''
}

onMounted(() => {
  marketStore.fetchDashboard()
  marketStore.fetchAllDimensions()
  signalStore.fetchCurrentSignals()
  signalStore.fetchSignalHistory()
  systemStore.fetchSourceStatus()
  // Re-show the mock banner when fresh mock data arrives.
  watch(mockBannerSources, (val) => {
    if (val.length) mockBannerVisible.value = true
  })
  pollStatus()
  pollTimer = setInterval(pollStatus, 5000)
  debugWsStateHandler = (s) => {
    wsState.value = s.connected ? 'OPEN' : 'CLOSED'
  }
  wsClient.onConnectionStateChange(debugWsStateHandler)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (debugWsStateHandler) {
    wsClient.offConnectionStateChange(debugWsStateHandler)
    debugWsStateHandler = null
  }
})

// `watch` is imported at the top of this file.

function formatGEX(val?: number): string {
  if (val == null) return '—'
  const abs = Math.abs(val)
  if (abs >= 1e9) return `${(val / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(val / 1e6).toFixed(2)}M`
  return val.toFixed(2)
}

function formatFunding(val?: number): string {
  if (val == null) return '—'
  return (val * 100).toFixed(4) + '%'
}
</script>

<style scoped>
/* DEBUG panel — 浮动右上角 */
.msr-debug-panel {
  position: fixed;
  top: 60px;
  right: 16px;
  z-index: 9999;
  background: rgba(10, 14, 24, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.4);
  border-radius: 8px;
  padding: 10px 12px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #0ff;
  min-width: 220px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}
.msr-debug-btn {
  display: block;
  width: 100%;
  background: rgba(0, 255, 255, 0.15);
  color: #0ff;
  border: 1px solid #0ff;
  border-radius: 4px;
  padding: 6px 10px;
  margin-bottom: 8px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
}
.msr-debug-btn:hover:not(:disabled) {
  background: rgba(0, 255, 255, 0.3);
}
.msr-debug-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}
.msr-debug-btn-sm {
  display: block;
  width: 100%;
  background: transparent;
  color: #888;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 3px 8px;
  margin-top: 6px;
  cursor: pointer;
  font-family: inherit;
  font-size: 11px;
}
.msr-debug-btn-sm:hover { color: #0ff; border-color: #0ff; }
.msr-debug-status {
  font-size: 11px;
  line-height: 1.5;
  color: #aaa;
  margin: 6px 0;
}
.msr-debug-status > div { display: flex; justify-content: space-between; gap: 8px; }
.msr-debug-log {
  margin-top: 6px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  font-size: 10px;
  color: #0f0;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: auto;
  gap: var(--spacing-md);
}
.grid-score { grid-column: 1; }
.grid-radar { grid-column: 2; }
.grid-gauge { grid-column: 3; }
.grid-signal { grid-column: 1; }
.grid-timeline { grid-column: 2; }
.grid-summary { grid-column: 3; }
.grid-sources { grid-column: 1 / -1; }

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.summary-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.summary-item { display: flex; flex-direction: column; gap: 4px; }
.summary-label { font-size: 11px; color: var(--text-muted); }
.summary-value { font-size: 18px; font-weight: 700; }
.source-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; }

@media (max-width: 1366px) {
  .dashboard-grid { grid-template-columns: repeat(2, 1fr); }
  .grid-sources { grid-column: 1 / -1; }
}

/* Banner styles */
.mock-warning-banner,
.error-banner,
.ws-warning-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: var(--spacing-md);
  border-radius: 8px;
  font-size: 13px;
}
.mock-warning-banner {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.5);
  color: var(--accent-amber);
}
.error-banner {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.55);
  color: var(--accent-red);
}
.error-banner-icon { font-size: 16px; line-height: 1; }
.error-banner-text { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.error-banner-detail { font-size: 12px; color: var(--text-secondary); font-weight: 400; }
.error-banner-close {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 4px;
}
.error-banner-close:hover { background: rgba(239, 68, 68, 0.15); }
.ws-warning-banner {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.5);
  color: var(--accent-indigo);
}
.ws-warning-icon { font-size: 16px; line-height: 1; }
.ws-warning-text { display: flex; flex-direction: column; gap: 2px; }
.ws-warning-detail { font-size: 12px; color: var(--text-secondary); font-weight: 400; }

.value-error { color: var(--accent-red) !important; }
</style>
