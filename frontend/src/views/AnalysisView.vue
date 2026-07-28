<template>
  <div class="analysis-view">
    <div class="analysis-grid">
      <!-- Scoring -->
      <div class="glass-card">
        <h3 class="section-title">综合评分</h3>
        <GaugeChart :value="scoring?.total_score ?? 0" :max="5.0" title="Total Score" :height="200" />
        <div class="scoring-detail" v-if="scoring">
          <div class="threshold-info">
            <span>LEVEL_1: ≥2.0</span>
            <span>LEVEL_2: ≥3.0</span>
            <span>LEVEL_3: ≥3.5</span>
          </div>
          <div class="hawkes" v-if="scoring.hawkes_branching_ratio != null">
            Hawkes 分支比: {{ scoring.hawkes_branching_ratio.toFixed(3) }}
          </div>
        </div>
      </div>

      <!-- GEX Analysis -->
      <div class="glass-card">
        <h3 class="section-title">GEX 分析</h3>
        <div v-if="gexAnalysis" class="analysis-content">
          <div class="metric-row" v-for="(val, key) in gexAnalysis.snapshot || {}" :key="key">
            <span class="metric-label">{{ key }}</span>
            <span class="metric-value">{{ formatVal(val) }}</span>
          </div>
        </div>
        <div v-else class="no-data">暂无数据</div>
      </div>

      <!-- VIX Analysis -->
      <div class="glass-card">
        <h3 class="section-title">VIX 分析</h3>
        <div v-if="vixAnalysis" class="analysis-content">
          <div class="metric-row"><span class="metric-label">VIX Spot</span><span class="metric-value">{{ vixAnalysis.vix_spot?.toFixed(2) }}</span></div>
          <div class="metric-row"><span class="metric-label">期限结构</span><span class="metric-value" :class="vixAnalysis.analysis?.contango ? 'text-green' : 'text-red'">{{ vixAnalysis.term_structure_state }}</span></div>
          <div class="metric-row"><span class="metric-label">恐慌溢价</span><span class="metric-value">{{ vixAnalysis.panic_premium?.toFixed(2) }}</span></div>
          <div class="metric-row"><span class="metric-label">高恐慌</span><span class="metric-value">{{ vixAnalysis.analysis?.high_panic ? '是' : '否' }}</span></div>
        </div>
        <div v-else class="no-data">暂无数据</div>
      </div>

      <!-- Crypto Analysis -->
      <div class="glass-card">
        <h3 class="section-title">加密分析</h3>
        <div v-if="cryptoAnalysis" class="analysis-content">
          <div class="metric-row"><span class="metric-label">杠杆清洗</span><span class="metric-value" :class="cryptoAnalysis.analysis?.leverage_cleanup_active ? 'text-red' : 'text-green'">{{ cryptoAnalysis.analysis?.leverage_cleanup_active ? '活跃' : '否' }}</span></div>
          <div class="metric-row"><span class="metric-label">资金费率</span><span class="metric-value" :class="cryptoAnalysis.analysis?.funding_negative ? 'text-red' : 'text-green'">{{ ((cryptoAnalysis.btc_funding_rate || 0) * 100).toFixed(4) }}%</span></div>
          <div class="metric-row"><span class="metric-label">OI 趋势</span><span class="metric-value">{{ cryptoAnalysis.analysis?.oi_declining ? '下降' : '稳定' }}</span></div>
        </div>
        <div v-else class="no-data">暂无数据</div>
      </div>

      <!-- Darkpool Analysis -->
      <div class="glass-card">
        <h3 class="section-title">暗池分析</h3>
        <div v-if="darkpoolAnalysis" class="analysis-content">
          <div class="metric-row"><span class="metric-label">DIX 看涨</span><span class="metric-value" :class="darkpoolAnalysis.analysis?.dix_bullish ? 'text-green' : 'text-red'">{{ darkpoolAnalysis.analysis?.dix_bullish ? '是' : '否' }}</span></div>
          <div class="metric-row"><span class="metric-label">EMA 金叉</span><span class="metric-value">{{ darkpoolAnalysis.analysis?.ema_bullish_cross ? '是' : '否' }}</span></div>
          <div class="metric-row"><span class="metric-label">动量反转</span><span class="metric-value">{{ darkpoolAnalysis.analysis?.momentum_reversing ? '是' : '否' }}</span></div>
        </div>
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAnalysisScoring, getAnalysisGEX, getAnalysisVIX, getAnalysisCrypto, getAnalysisDarkpool } from '@/api/analysis'
import GaugeChart from '@/components/charts/GaugeChart.vue'

const scoring = ref<any>(null)
const gexAnalysis = ref<any>(null)
const vixAnalysis = ref<any>(null)
const cryptoAnalysis = ref<any>(null)
const darkpoolAnalysis = ref<any>(null)

function formatVal(val: any): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'number') return val.toFixed(4)
  return String(val)
}

onMounted(async () => {
  const [s, g, v, c, d] = await Promise.all([
    getAnalysisScoring().catch(() => ({ data: null })),
    getAnalysisGEX().catch(() => ({ data: null })),
    getAnalysisVIX().catch(() => ({ data: null })),
    getAnalysisCrypto().catch(() => ({ data: null })),
    getAnalysisDarkpool().catch(() => ({ data: null })),
  ])
  scoring.value = s.data
  gexAnalysis.value = g.data
  vixAnalysis.value = v.data
  cryptoAnalysis.value = c.data
  darkpoolAnalysis.value = d.data
})
</script>

<style scoped>
.analysis-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.metric-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.metric-label { font-size: 12px; color: var(--text-muted); }
.metric-value { font-size: 13px; font-weight: 600; }
.scoring-detail { margin-top: 8px; }
.threshold-info { display: flex; justify-content: space-around; font-size: 11px; color: var(--text-muted); }
.hawkes { text-align: center; font-size: 12px; color: var(--text-secondary); margin-top: 8px; }
.no-data { text-align: center; color: var(--text-muted); padding: 32px; }
</style>
