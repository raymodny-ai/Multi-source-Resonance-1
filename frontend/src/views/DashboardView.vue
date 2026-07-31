<template>
  <div class="dashboard-view">
    <!-- DEBUG: 临时浮动面板 — 手动触发 fetchDashboard + 显示 ws 状态 -->
    <div class="msr-debug-panel">
      <button class="msr-debug-btn" @click="manualRefresh" :disabled="refreshing">
        {{ refreshing ? '⟳ 拉取中...' : '🔄 手动刷新数据' }}
      </button>
      <div class="msr-debug-status">
        <div>WS: {{ wsState }}</div>
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
            <span class="summary-value">{{ marketStore.vixData?.vix_spot?.toFixed(2) ?? '—' }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">BTC Funding</span>
            <span class="summary-value">{{ formatFunding(marketStore.cryptoData?.btc_funding_rate) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">DIX Value</span>
            <span class="summary-value">{{ marketStore.darkpoolData?.dix_value?.toFixed(2) ?? '—' }}</span>
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
import { onMounted, onUnmounted, computed, ref } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useSignalStore } from '@/stores/signals'
import { useSystemStore } from '@/stores/system'
import wsClient from '@/api/websocket'
import ScoreOverview from '@/components/dashboard/ScoreOverview.vue'
import SignalCard from '@/components/dashboard/SignalCard.vue'
import SourceStatusCard from '@/components/dashboard/SourceStatusCard.vue'
import RadarChart from '@/components/charts/RadarChart.vue'
import GaugeChart from '@/components/charts/GaugeChart.vue'
import SignalTimeline from '@/components/signals/SignalTimeline.vue'

const marketStore = useMarketStore()
const signalStore = useSignalStore()
const systemStore = useSystemStore()

const gexNet = computed(() => marketStore.dashboardData?.gex?.net_gex)
const gexClass = computed(() => (gexNet.value && gexNet.value > 0) ? 'text-green' : 'text-red')

// ─── DEBUG: 手动刷新 + 状态显示 ──────────────────────────────
const refreshing = ref(false)
const showDebugLog = ref(false)
const debugLogText = ref('')
const wsState = ref('?')
const pipelineCycle = ref('?')
const lastFetchAgo = ref('?')
const gexTimestamp = ref('?')
let pollTimer: ReturnType<typeof setInterval> | null = null

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
  // ws state
  if (wsClient && (wsClient as any).ws) {
    const rs = (wsClient as any).ws.readyState
    wsState.value = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][rs] || `state=${rs}`
  } else {
    wsState.value = 'no ws'
  }
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

onMounted(() => {
  marketStore.fetchDashboard()
  marketStore.fetchAllDimensions()
  signalStore.fetchCurrentSignals()
  signalStore.fetchSignalHistory()
  systemStore.fetchSourceStatus()
  pollStatus()
  pollTimer = setInterval(pollStatus, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

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
</style>
