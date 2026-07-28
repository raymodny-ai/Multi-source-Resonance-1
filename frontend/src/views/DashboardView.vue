<template>
  <div class="dashboard-view">
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
import { onMounted, computed } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useSignalStore } from '@/stores/signals'
import { useSystemStore } from '@/stores/system'
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

onMounted(() => {
  marketStore.fetchDashboard()
  marketStore.fetchAllDimensions()
  signalStore.fetchCurrentSignals()
  signalStore.fetchSignalHistory()
  systemStore.fetchSourceStatus()
})
</script>

<style scoped>
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
