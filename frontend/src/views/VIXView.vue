<template>
  <div class="vix-view">
    <div class="vix-grid">
      <!-- Current VIX (live) -->
      <div class="glass-card">
        <h3 class="section-title">当前 VIX</h3>
        <div class="vix-current" v-if="latest">
          <div class="vix-big" :class="regimeClass(latestRegime)">{{ latest.vix_spot?.toFixed(2) ?? '—' }}</div>
          <div class="vix-regime">{{ latestRegime?.toUpperCase() ?? '—' }}</div>
          <div class="vix-details">
            <div class="vix-row"><span>VX 3M (proxy)</span><span>{{ (latest as any).vx_3m_proxy?.toFixed(2) ?? latest.vx1?.toFixed(2) ?? '—' }}</span></div>
            <div class="vix-row"><span>期限结构</span><span :class="latest.term_structure_state === 'contango' ? 'text-green' : latest.term_structure_state === 'backwardation' ? 'text-red' : 'text-yellow'">{{ latest.term_structure_state ?? '—' }}</span></div>
            <div class="vix-row"><span>期限结构比率</span><span>{{ latest.term_structure_ratio != null ? (latest.term_structure_ratio * 100).toFixed(2) + '%' : '—' }}</span></div>
            <div class="vix-row"><span>恐慌溢价</span><span>{{ latest.panic_premium?.toFixed(2) ?? '—' }}</span></div>
          </div>
        </div>
        <div v-else class="no-data">无 VIX 数据</div>
      </div>

      <!-- Term Structure Chart (live cycle snapshots) -->
      <div class="glass-card">
        <h3 class="section-title">VIX 期限结构走势 (live)</h3>
        <TermStructure :data="history" :height="350" />
      </div>

      <!-- Daily Term Structure History (FRED VIXCLS + VXVCLS, 500 days) -->
      <div class="glass-card full-width">
        <div class="card-header">
          <h3 class="section-title">期限结构历史 (FRED daily, {{ tsHistory.length }} 天)</h3>
          <div class="day-selector">
            <button v-for="d in [30, 90, 180, 365, 730]" :key="d"
              :class="['day-btn', { active: tsDays === d }]"
              @click="setTSDays(d)">
              {{ d === 730 ? '2Y' : d + 'd' }}
            </button>
          </div>
        </div>
        <LineChart
          :x-data="tsXData"
          :series="tsSeries"
          :height="380"
          :area-style="false"
        />
      </div>

      <!-- VIX Spot Trend + Regime bands (daily) -->
      <div class="glass-card full-width">
        <h3 class="section-title">VIX Spot 走势 + Regime</h3>
        <LineChart
          :x-data="tsXData"
          :series="regimeSeries"
          :height="320"
          :area-style="true"
        />
      </div>

      <!-- Panic Premium + Term Structure Ratio over time -->
      <div class="glass-card full-width">
        <h3 class="section-title">恐慌溢价 & 期限结构比率历史</h3>
        <LineChart
          :x-data="tsXData"
          :series="panicSeries"
          :height="280"
          :area-style="false"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getVIXLatest, getVIXHistory, getVIXTermStructureHistory, type VIXData, type VIXTermStructureHistoryRow } from '@/api/vix'
import TermStructure from '@/components/vix/TermStructure.vue'
import LineChart from '@/components/charts/LineChart.vue'

const latest = ref<VIXData | null>(null)
const history = ref<VIXData[]>([])
const tsHistory = ref<VIXTermStructureHistoryRow[]>([])
const tsDays = ref(365)

const latestRegime = computed(() => {
  const v = latest.value?.vix_spot ?? 0
  if (v < 15) return 'low'
  if (v < 25) return 'normal'
  if (v < 35) return 'elevated'
  return 'panic'
})

function regimeClass(r: string | null) {
  if (!r) return ''
  if (r === 'low') return 'regime-low'
  if (r === 'normal') return 'regime-normal'
  if (r === 'elevated') return 'regime-elevated'
  if (r === 'panic') return 'regime-panic'
  return ''
}

const xData = computed(() =>
  history.value.map((d) => {
    try { return new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.timestamp }
  })
)
const spotData = computed(() => history.value.map((d) => d.vix_spot))

// Daily term structure (filtered by tsDays)
const tsXData = computed(() => tsHistory.value.map((d) => {
  try { return new Date(d.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.date }
}))
const tsSeries = computed(() => [
  { name: 'VIX Spot', data: tsHistory.value.map((d) => d.vix_spot), color: '#ef4444' },
  { name: 'VX 3M Proxy', data: tsHistory.value.map((d) => d.vx_3m_proxy), color: '#6366f1' },
])
const regimeSeries = computed(() => {
  // VIX spot with regime band shading — convert regime to numeric for viz
  const regimeColors: Record<string, string> = {
    low: '#10b981',
    normal: '#3b82f6',
    elevated: '#f59e0b',
    panic: '#ef4444',
  }
  return [
    { name: 'VIX Spot (regime色)', data: tsHistory.value.map((d) => d.vix_spot), color: '#ef4444' },
  ]
})
const panicSeries = computed(() => [
  { name: '恐慌溢价 (VIX-VX3M)', data: tsHistory.value.map((d) => d.panic_premium), color: '#f97316' },
  { name: '期限结构比率 (%)', data: tsHistory.value.map((d) => d.term_structure_ratio != null ? d.term_structure_ratio * 100 : null), color: '#8b5cf6' },
])

async function loadTSDays(days: number) {
  try {
    const r = await getVIXTermStructureHistory(days)
    tsHistory.value = r.data
  } catch (e) {
    console.error('VIX term-structure-history fetch failed:', e)
  }
}

function setTSDays(d: number) {
  tsDays.value = d
  loadTSDays(d)
}

watch(tsDays, (v) => loadTSDays(v))

onMounted(async () => {
  try {
    const [latestResp, histResp] = await Promise.all([
      getVIXLatest(),
      getVIXHistory(90),
      loadTSDays(tsDays.value),
    ])
    latest.value = latestResp.data
    history.value = histResp.data
  } catch (e) {
    console.error('VIX fetch failed:', e)
  }
})
</script>

<style scoped>
.vix-view { width: 100%; }
.vix-grid { display: grid; grid-template-columns: 1fr 2fr; gap: var(--spacing-md); }
.vix-grid .full-width { grid-column: 1 / -1; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-sm); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.vix-big { font-size: 48px; font-weight: 800; text-align: center; margin: 16px 0 4px; transition: color 0.3s; }
.regime-low { color: #10b981; }
.regime-normal { color: #3b82f6; }
.regime-elevated { color: #f59e0b; }
.regime-panic { color: #ef4444; }
.vix-regime { text-align: center; font-size: 11px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.1em; margin-bottom: 12px; }
.vix-details { display: flex; flex-direction: column; gap: 8px; }
.vix-row { display: flex; justify-content: space-between; font-size: 14px; color: var(--text-secondary); }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
.day-selector { display: flex; gap: 4px; }
.day-btn { padding: 4px 10px; font-size: 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: var(--text-secondary); cursor: pointer; transition: all 0.2s; }
.day-btn:hover { background: rgba(255,255,255,0.1); }
.day-btn.active { background: rgba(99,102,241,0.2); border-color: #6366f1; color: #6366f1; }
</style>