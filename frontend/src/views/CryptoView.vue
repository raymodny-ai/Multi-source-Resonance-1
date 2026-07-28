<template>
  <div class="crypto-view">
    <div class="crypto-grid">
      <div class="glass-card">
        <h3 class="section-title">当前状态</h3>
        <div class="crypto-current" v-if="latest">
          <div class="metric-row">
            <span class="metric-label">BTC Funding Rate</span>
            <span class="metric-value" :class="latest.btc_funding_rate < 0 ? 'text-red' : 'text-green'">{{ (latest.btc_funding_rate * 100).toFixed(4) }}%</span>
          </div>
          <div class="metric-row"><span class="metric-label">BTC OI</span><span class="metric-value">{{ latest.btc_oi?.toFixed(0) ?? '—' }}</span></div>
          <div class="metric-row"><span class="metric-label">OI Change 1h</span><span class="metric-value" :class="(latest.oi_change_1h || 0) < 0 ? 'text-red' : 'text-green'">{{ ((latest.oi_change_1h || 0) * 100).toFixed(2) }}%</span></div>
          <div class="metric-row"><span class="metric-label">ELR</span><span class="metric-value">{{ latest.cryptoquant_elr?.toFixed(4) ?? '—' }}</span></div>
          <div class="signal-row">
            <span class="badge" :class="latest.leverage_cleanup ? 'badge-red' : 'badge-green'">{{ latest.leverage_cleanup ? '杠杆清洗中' : '正常' }}</span>
            <span class="badge" :class="latest.oi_crash ? 'badge-red' : 'badge-green'">{{ latest.oi_crash ? 'OI 暴跌' : 'OI 稳定' }}</span>
            <span class="badge" :class="latest.funding_anomaly ? 'badge-amber' : 'badge-green'">{{ latest.funding_anomaly ? '资金费率异常' : '正常' }}</span>
          </div>
        </div>
        <div v-else class="no-data">无加密数据</div>
      </div>

      <div class="glass-card">
        <h3 class="section-title">Funding Rate 走势</h3>
        <LineChart :x-data="xData" :series="[{ name: 'Funding Rate', data: fundingData, color: '#f59e0b' }]" :height="300" />
      </div>

      <div class="glass-card">
        <h3 class="section-title">OI 变化</h3>
        <LineChart :x-data="xData" :series="[{ name: 'OI Change 1h', data: oiData, color: '#22d3ee' }]" :height="300" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getCryptoLatest, getCryptoHistory, type CryptoData } from '@/api/crypto'
import LineChart from '@/components/charts/LineChart.vue'

const latest = ref<CryptoData | null>(null)
const history = ref<CryptoData[]>([])

const xData = computed(() => history.value.map((d) => {
  try { return new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.timestamp }
}))
const fundingData = computed(() => history.value.map((d) => d.btc_funding_rate * 100))
const oiData = computed(() => history.value.map((d) => (d.oi_change_1h || 0) * 100))

onMounted(async () => {
  try {
    const [latestResp, histResp] = await Promise.all([getCryptoLatest(), getCryptoHistory(30)])
    latest.value = latestResp.data
    history.value = histResp.data
  } catch (e) { console.error('Crypto fetch failed:', e) }
})
</script>

<style scoped>
.crypto-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.metric-label { font-size: 13px; color: var(--text-muted); }
.metric-value { font-size: 14px; font-weight: 600; }
.signal-row { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
</style>
