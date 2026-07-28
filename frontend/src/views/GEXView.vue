<template>
  <div class="gex-view">
    <div class="view-header">
      <div class="symbol-selector">
        <button
          v-for="sym in symbols"
          :key="sym"
          class="sym-btn"
          :class="{ active: selectedSymbol === sym }"
          @click="selectedSymbol = sym"
        >{{ sym }}</button>
      </div>
    </div>

    <LoadingSpinner v-if="loading" text="Loading GEX data..." />

    <div v-else class="gex-grid">
      <!-- Key Levels -->
      <div class="glass-card levels-card">
        <h3 class="section-title">关键价位</h3>
        <div class="levels-grid" v-if="levels">
          <div class="level-item"><span class="level-label">Call Wall</span><span class="level-val text-green">{{ levels.call_wall }}</span></div>
          <div class="level-item"><span class="level-label">Put Wall</span><span class="level-val text-red">{{ levels.put_wall }}</span></div>
          <div class="level-item"><span class="level-label">Zero Gamma</span><span class="level-val text-amber">{{ levels.zero_gamma_level }}</span></div>
          <div class="level-item"><span class="level-label">Spot</span><span class="level-val">{{ levels.spot_price }}</span></div>
          <div class="level-item"><span class="level-label">Net GEX</span><span class="level-val" :class="levels.net_gex > 0 ? 'text-green' : 'text-red'">{{ formatGEX(levels.net_gex) }}</span></div>
        </div>
      </div>

      <!-- GEX Curve -->
      <div class="glass-card">
        <h3 class="section-title">GEX 曲线 (90天)</h3>
        <GEXCurve :data="longHistory" :height="300" />
      </div>

      <!-- Strike Distribution -->
      <div class="glass-card">
        <h3 class="section-title">Strike 分布</h3>
        <StrikeDistribution v-if="strikes.length" :strikes="strikes" :height="300" />
        <div v-else class="no-data">无 Strike 数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getGEXDashboardView, type GEXStrike } from '@/api/gex'
import GEXCurve from '@/components/gex/GEXCurve.vue'
import StrikeDistribution from '@/components/gex/StrikeDistribution.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const symbols = ['SPX', 'SPY', 'QQQ', 'IWM', 'NDX', 'VIX']
const selectedSymbol = ref('SPX')
const loading = ref(false)
const levels = ref<any>(null)
const longHistory = ref<any[]>([])
const strikes = ref<GEXStrike[]>([])

function formatGEX(val: number): string {
  const abs = Math.abs(val)
  if (abs >= 1e9) return `${(val / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(val / 1e6).toFixed(2)}M`
  return val.toFixed(2)
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await getGEXDashboardView(selectedSymbol.value, { long_days: 90, strikes_limit: 200 })
    levels.value = data.levels
    longHistory.value = data.long_history || []
    strikes.value = data.strikes?.strikes || []
  } catch (e) {
    console.error('GEX fetch failed:', e)
  } finally {
    loading.value = false
  }
}

watch(selectedSymbol, fetchData)
onMounted(fetchData)
</script>

<style scoped>
.view-header { margin-bottom: var(--spacing-lg); }
.symbol-selector { display: flex; gap: 8px; }
.sym-btn { background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); padding: 6px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s; }
.sym-btn:hover { background: rgba(99,102,241,0.1); }
.sym-btn.active { background: rgba(99,102,241,0.2); color: var(--accent-indigo); border-color: var(--accent-indigo); }
.gex-grid { display: grid; grid-template-columns: 1fr 2fr; gap: var(--spacing-md); }
.levels-card { grid-row: span 2; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; letter-spacing: 0.5px; }
.levels-grid { display: flex; flex-direction: column; gap: 16px; }
.level-item { display: flex; justify-content: space-between; align-items: center; }
.level-label { font-size: 13px; color: var(--text-muted); }
.level-val { font-size: 18px; font-weight: 700; }
.no-data { text-align: center; color: var(--text-muted); padding: 48px; }
</style>
