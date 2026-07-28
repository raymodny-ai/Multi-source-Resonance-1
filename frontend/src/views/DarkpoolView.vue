<template>
  <div class="darkpool-view">
    <div class="dp-grid">
      <div class="glass-card">
        <h3 class="section-title">当前暗池指标</h3>
        <div v-if="latest">
          <div class="metric-row"><span class="metric-label">DIX Value</span><span class="metric-value" :class="(latest.dix_value || 0) > 50 ? 'text-green' : 'text-red'">{{ latest.dix_value?.toFixed(2) ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">V_Net</span><span class="metric-value">{{ latest.v_net?.toFixed(2) ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">EMA Fast (5)</span><span class="metric-value">{{ latest.ema_fast_5?.toFixed(2) ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">EMA Slow (20)</span><span class="metric-value">{{ latest.ema_slow_20?.toFixed(2) ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">Zero Cross</span><span class="metric-value">{{ latest.zero_cross_signal ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">Momentum</span><span class="metric-value">{{ latest.momentum_reversal_signal ?? '—' }}</span></div>
          <div class="signal-row">
            <span class="badge" :class="latest.aggregated_signal ? 'badge-green' : 'badge-red'">{{ latest.aggregated_signal ? '看涨' : '看跌' }}</span>
          </div>
        </div>
        <div v-else class="no-data">无暗池数据</div>
      </div>

      <!-- DIX Daily Trend (from /api/darkpool/flow) -->
      <div class="glass-card">
        <h3 class="section-title">DIX 走势 (daily)</h3>
        <LineChart :x-data="xData" :series="[{ name: 'DIX', data: dixData, color: '#6366f1' }]" :height="300" :area-style="true" />
      </div>

      <!-- V_Net + EMA -->
      <div class="glass-card full-width">
        <h3 class="section-title">V_Net & EMA 走势</h3>
        <LineChart :x-data="xData" :series="vnetSeries" :height="280" :area-style="false" />
      </div>

      <!-- Intraday History (SqueezeMetrics DIX/GEX/SPX, 90 days) -->
      <div class="glass-card full-width">
        <div class="card-header">
          <h3 class="section-title">SqueezeMetrics 暗池历史 (DIX/GEX/SPX, {{ intradayHistory.length }} 天)</h3>
          <div class="day-selector">
            <button v-for="d in [30, 60, 90]" :key="d"
              :class="['day-btn', { active: intradayDays === d }]"
              @click="setIntradayDays(d)">
              {{ d }}d
            </button>
          </div>
        </div>
        <LineChart
          :x-data="intradayXData"
          :series="dixGexSeries"
          :height="340"
          :area-style="false"
        />
      </div>

      <!-- SPX Price Co-movement -->
      <div class="glass-card full-width">
        <h3 class="section-title">SPX 价格 vs DIX (历史共动)</h3>
        <LineChart
          :x-data="intradayXData"
          :series="spxDixSeries"
          :height="320"
          :area-style="false"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getDarkpoolLatest, getDarkpoolFlow, getDarkpoolHistoryIntraday, type DarkpoolData, type DarkpoolFlow, type DarkpoolHistoryIntradayRow } from '@/api/darkpool'
import LineChart from '@/components/charts/LineChart.vue'

const latest = ref<DarkpoolData | null>(null)
const flow = ref<DarkpoolFlow[]>([])
const intradayHistory = ref<DarkpoolHistoryIntradayRow[]>([])
const intradayDays = ref(90)

const xData = computed(() => flow.value.map((d) => {
  try { return new Date(d.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.date }
}))
const dixData = computed(() => flow.value.map((d) => d.dix_value))
const vnetSeries = computed(() => [
  { name: 'V_Net', data: flow.value.map((d) => d.v_net), color: '#6366f1' },
  { name: 'EMA 5', data: flow.value.map((d) => d.ema_fast_5), color: '#22d3ee' },
  { name: 'EMA 20', data: flow.value.map((d) => d.ema_slow_20), color: '#f59e0b' },
])

// Intraday chart data (SqueezeMetrics)
const intradayXData = computed(() => intradayHistory.value.map((d) => {
  try { return new Date(d.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.date }
}))
const dixGexSeries = computed(() => [
  { name: 'DIX (%)', data: intradayHistory.value.map((d) => d.dix_value), color: '#6366f1' },
  { name: 'GEX (B$)', data: intradayHistory.value.map((d) => d.gex_value != null ? d.gex_value / 1e9 : null), color: '#f59e0b' },
])
const spxDixSeries = computed(() => [
  { name: 'SPX Price', data: intradayHistory.value.map((d) => d.spx_price), color: '#10b981' },
  { name: 'DIX (%)', data: intradayHistory.value.map((d) => d.dix_value), color: '#6366f1' },
])

async function loadIntraday(days: number) {
  try {
    const r = await getDarkpoolHistoryIntraday(days)
    intradayHistory.value = r.data
  } catch (e) {
    console.error('Darkpool history-intraday fetch failed:', e)
  }
}

function setIntradayDays(d: number) {
  intradayDays.value = d
  loadIntraday(d)
}

watch(intradayDays, (v) => loadIntraday(v))

onMounted(async () => {
  try {
    const [latestResp, flowResp] = await Promise.all([
      getDarkpoolLatest(),
      getDarkpoolFlow(90),
      loadIntraday(intradayDays.value),
    ])
    latest.value = latestResp.data
    flow.value = flowResp.data
  } catch (e) { console.error('Darkpool fetch failed:', e) }
})
</script>

<style scoped>
.darkpool-view { width: 100%; }
.dp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.dp-grid .full-width { grid-column: 1 / -1; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-sm); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.metric-label { color: var(--text-secondary); font-size: 13px; }
.metric-value { color: var(--text-primary); font-size: 14px; font-weight: 600; font-family: var(--font-mono, monospace); }
.signal-row { margin-top: 12px; text-align: center; }
.badge { display: inline-block; padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 700; }
.badge-green { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); }
.badge-red { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
.day-selector { display: flex; gap: 4px; }
.day-btn { padding: 4px 10px; font-size: 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: var(--text-secondary); cursor: pointer; transition: all 0.2s; }
.day-btn:hover { background: rgba(255,255,255,0.1); }
.day-btn.active { background: rgba(99,102,241,0.2); border-color: #6366f1; color: #6366f1; }
.text-green { color: #10b981; }
.text-red { color: #ef4444; }
.text-yellow { color: #f59e0b; }
</style>