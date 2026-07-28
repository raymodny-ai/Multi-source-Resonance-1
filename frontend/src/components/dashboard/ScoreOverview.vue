<template>
  <div class="score-overview glass-card">
    <div class="score-main">
      <div class="score-value" :class="levelColor">{{ totalScore.toFixed(2) }}</div>
      <div class="score-label">共振评分</div>
      <div class="level-badge" :class="levelClass">{{ alertLevel }}</div>
    </div>
    <div class="dimension-bars">
      <div v-for="dim in dimensions" :key="dim.name" class="dim-row">
        <span class="dim-name">{{ dim.name }}</span>
        <div class="dim-bar-bg">
          <div class="dim-bar" :style="{ width: dim.pct + '%', background: dim.color }"></div>
        </div>
        <span class="dim-value">{{ dim.value.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  totalScore: number
  alertLevel: string
  dimensions: { gex: number; vix: number; crypto: number; darkpool: number }
}>()

const levelClass = computed(() => props.alertLevel.toLowerCase())
const levelColor = computed(() => {
  if (props.alertLevel === 'LEVEL_3') return 'text-red'
  if (props.alertLevel === 'LEVEL_2') return 'text-amber'
  return 'text-cyan'
})

const dimensions = computed(() => [
  { name: 'GEX', value: props.dimensions.gex, max: 2.5, color: '#6366f1', pct: (props.dimensions.gex / 2.5) * 100 },
  { name: 'VIX', value: props.dimensions.vix, max: 1.5, color: '#22d3ee', pct: (props.dimensions.vix / 1.5) * 100 },
  { name: 'Crypto', value: props.dimensions.crypto, max: 2.0, color: '#f59e0b', pct: (props.dimensions.crypto / 2.0) * 100 },
  { name: 'Darkpool', value: props.dimensions.darkpool, max: 2.0, color: '#10b981', pct: (props.dimensions.darkpool / 2.0) * 100 },
])
</script>

<style scoped>
.score-overview { padding: var(--spacing-lg); }
.score-main { text-align: center; margin-bottom: var(--spacing-md); }
.score-value { font-size: 48px; font-weight: 800; line-height: 1; }
.score-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.level-badge { display: inline-block; margin-top: 8px; padding: 2px 12px; border-radius: 12px; font-size: 12px; font-weight: 700; }
.level-badge.level_3 { background: rgba(239,68,68,0.2); color: var(--accent-red); }
.level-badge.level_2 { background: rgba(245,158,11,0.2); color: var(--accent-amber); }
.level-badge.level_1, .level-badge.none { background: rgba(255,255,255,0.05); color: var(--text-muted); }
.dimension-bars { display: flex; flex-direction: column; gap: 8px; }
.dim-row { display: flex; align-items: center; gap: 8px; }
.dim-name { width: 60px; font-size: 12px; color: var(--text-secondary); text-align: right; }
.dim-bar-bg { flex: 1; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
.dim-bar { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.dim-value { width: 36px; font-size: 12px; color: var(--text-secondary); text-align: right; }
</style>
