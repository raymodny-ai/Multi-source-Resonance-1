<template>
  <div class="signal-card glass-card" :class="levelClass">
    <div v-if="hasMockWarning" class="mock-warning">
      <span class="mock-warning-icon">⚠</span>
      <span class="mock-warning-text">
        信号分数基于模拟数据 ({{ mockSourcesLabel }})
      </span>
    </div>
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
import { useMarketStore } from '@/stores/market'

const props = defineProps<{ signal?: SignalAlert | null }>()
const marketStore = useMarketStore()

const levelClass = computed(() => {
  const level = props.signal?.alert_level ?? 'NONE'
  return level.toLowerCase()
})

const hasMockWarning = computed(() => marketStore.hasMockData)
const mockSourcesLabel = computed(() => {
  const names = Object.values(marketStore.mockSources).map((m) => m.source)
  return names.length ? names.join('、') : ''
})

function formatTime(ts?: string): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}
</script>

<style scoped>
.signal-card { padding: var(--spacing-md); transition: transform 0.2s; }
.signal-card:hover { transform: translateY(-2px); }
.mock-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 6px;
  color: var(--accent-amber);
  font-size: 12px;
}
.mock-warning-icon { font-size: 14px; }
.mock-warning-text { flex: 1; }
.signal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.signal-level { font-weight: 700; font-size: 13px; padding: 2px 10px; border-radius: 12px; }
.signal-level.level_3 { background: rgba(239,68,68,0.2); color: var(--accent-red); }
.signal-level.level_2 { background: rgba(245,158,11,0.2); color: var(--accent-amber); }
.signal-level.level_1, .signal-level.none { background: rgba(255,255,255,0.05); color: var(--text-muted); }
.signal-time { font-size: 11px; color: var(--text-muted); }
.signal-score { font-size: 32px; font-weight: 800; text-align: center; margin: 8px 0; }
.signal-dims { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); }
</style>

