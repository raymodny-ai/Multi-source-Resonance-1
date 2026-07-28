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

      <div class="glass-card">
        <h3 class="section-title">DIX 走势</h3>
        <LineChart :x-data="xData" :series="[{ name: 'DIX', data: dixData, color: '#6366f1' }]" :height="300" />
      </div>

      <div class="glass-card">
        <h3 class="section-title">V_Net & EMA</h3>
        <LineChart :x-data="xData" :series="vnetSeries" :height="300" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDarkpoolLatest, getDarkpoolFlow, type DarkpoolData, type DarkpoolFlow } from '@/api/darkpool'
import LineChart from '@/components/charts/LineChart.vue'

const latest = ref<DarkpoolData | null>(null)
const flow = ref<DarkpoolFlow[]>([])

const xData = computed(() => flow.value.map((d) => {
  try { return new Date(d.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.date }
}))
const dixData = computed(() => flow.value.map((d) => d.dix_value))
const vnetSeries = computed(() => [
  { name: 'V_Net', data: flow.value.map((d) => d.v_net), color: '#6366f1' },
  { name: 'EMA 5', data: flow.value.map((d) => d.ema_fast_5), color: '#22d3ee' },
  { name: 'EMA 20', data: flow.value.map((d) => d.ema_slow_20), color: '#f59e0b' },
])

onMounted(async () => {
  try {
    const [latestResp, flowResp] = await Promise.all([getDarkpoolLatest(), getDarkpoolFlow(90)])
    latest.value = latestResp.data
    flow.value = flowResp.data
  } catch (e) { console.error('Darkpool fetch failed:', e) }
})
</script>

<style scoped>
.dp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.metric-label { font-size: 13px; color: var(--text-muted); }
.metric-value { font-size: 14px; font-weight: 600; }
.signal-row { display: flex; gap: 8px; margin-top: 16px; }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
</style>
