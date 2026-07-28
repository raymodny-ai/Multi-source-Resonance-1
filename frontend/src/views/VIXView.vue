<template>
  <div class="vix-view">
    <div class="vix-grid">
      <!-- Current VIX -->
      <div class="glass-card">
        <h3 class="section-title">当前 VIX</h3>
        <div class="vix-current" v-if="latest">
          <div class="vix-big">{{ latest.vix_spot?.toFixed(2) ?? '—' }}</div>
          <div class="vix-details">
            <div class="vix-row"><span>VX1</span><span>{{ latest.vx1?.toFixed(2) }}</span></div>
            <div class="vix-row"><span>VX2</span><span>{{ latest.vx2?.toFixed(2) }}</span></div>
            <div class="vix-row"><span>期限结构</span><span :class="latest.term_structure_state === 'contango' ? 'text-green' : 'text-red'">{{ latest.term_structure_state }}</span></div>
            <div class="vix-row"><span>恐慌溢价</span><span>{{ latest.panic_premium?.toFixed(2) }}</span></div>
          </div>
        </div>
        <div v-else class="no-data">无 VIX 数据</div>
      </div>

      <!-- Term Structure Chart -->
      <div class="glass-card">
        <h3 class="section-title">VIX 期限结构走势</h3>
        <TermStructure :data="history" :height="350" />
      </div>

      <!-- VIX Trend -->
      <div class="glass-card">
        <h3 class="section-title">VIX Spot 走势</h3>
        <LineChart
          :x-data="xData"
          :series="[{ name: 'VIX Spot', data: spotData, color: '#ef4444' }]"
          :height="300"
          :area-style="true"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getVIXLatest, getVIXHistory, type VIXData } from '@/api/vix'
import TermStructure from '@/components/vix/TermStructure.vue'
import LineChart from '@/components/charts/LineChart.vue'

const latest = ref<VIXData | null>(null)
const history = ref<VIXData[]>([])

const xData = computed(() =>
  history.value.map((d) => {
    try { return new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.timestamp }
  })
)
const spotData = computed(() => history.value.map((d) => d.vix_spot))

onMounted(async () => {
  try {
    const [latestResp, histResp] = await Promise.all([getVIXLatest(), getVIXHistory(90)])
    latest.value = latestResp.data
    history.value = histResp.data
  } catch (e) {
    console.error('VIX fetch failed:', e)
  }
})
</script>

<style scoped>
.vix-grid { display: grid; grid-template-columns: 1fr 2fr; gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.vix-big { font-size: 48px; font-weight: 800; text-align: center; margin: 16px 0; }
.vix-details { display: flex; flex-direction: column; gap: 8px; }
.vix-row { display: flex; justify-content: space-between; font-size: 14px; color: var(--text-secondary); }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
</style>
