<template>
  <div class="signal-card glass-card" :class="levelClass">
    <div class="signal-header">
      <span class="signal-level" :class="levelClass">{{ signal?.alert_level ?? 'NONE' }}</span>
      <span class="signal-time">{{ formatTime(signal?.trigger_time) }}</span>
    </div>
    <div class="signal-score">{{ (signal?.total_score ?? 0).toFixed(2) }}</div>
    <div class="signal-dims">
      <span>GEX: {{ (signal?.gex_score ?? 0).toFixed(2) }}</span>
      <span>VIX: {{ (signal?.vix_score ?? 0).toFixed(2) }}</span>
      <span>CRY: {{ (signal?.crypto_score ?? 0).toFixed(2) }}</span>
      <span>DRK: {{ (signal?.darkpool_score ?? 0).toFixed(2) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SignalAlert } from '@/api/signals'

const props = defineProps<{ signal?: SignalAlert | null }>()

const levelClass = computed(() => {
  const level = props.signal?.alert_level ?? 'NONE'
  return level.toLowerCase()
})

function formatTime(ts?: string): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}
</script>

<style scoped>
.signal-card { padding: var(--spacing-md); transition: transform 0.2s; }
.signal-card:hover { transform: translateY(-2px); }
.signal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.signal-level { font-weight: 700; font-size: 13px; padding: 2px 10px; border-radius: 12px; }
.signal-level.level_3 { background: rgba(239,68,68,0.2); color: var(--accent-red); }
.signal-level.level_2 { background: rgba(245,158,11,0.2); color: var(--accent-amber); }
.signal-level.level_1, .signal-level.none { background: rgba(255,255,255,0.05); color: var(--text-muted); }
.signal-time { font-size: 11px; color: var(--text-muted); }
.signal-score { font-size: 32px; font-weight: 800; text-align: center; margin: 8px 0; }
.signal-dims { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); }
</style>
