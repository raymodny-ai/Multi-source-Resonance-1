<template>
  <div class="source-card glass-card">
    <div class="source-header">
      <span class="source-name">{{ source.name }}</span>
      <span class="status-dot" :class="source.status"></span>
    </div>
    <div class="source-meta">
      <span :class="'badge badge-' + statusBadgeClass">{{ source.status.toUpperCase() }}</span>
      <span class="availability" v-if="source.availability_pct != null">
        {{ source.availability_pct.toFixed(0) }}%
      </span>
    </div>
    <div class="source-detail" v-if="source.age_minutes != null">
      延迟: {{ formatAge(source.age_minutes) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SourceStatus } from '@/api/system'

const props = defineProps<{ source: SourceStatus }>()

const statusBadgeClass = computed(() => {
  if (props.source.status === 'online') return 'green'
  if (props.source.status === 'degraded') return 'amber'
  return 'red'
})

function formatAge(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)}h`
  return `${(minutes / 1440).toFixed(1)}d`
}
</script>

<style scoped>
.source-card { padding: var(--spacing-md); }
.source-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.source-name { font-size: 13px; font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.online { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
.status-dot.degraded { background: var(--accent-amber); }
.status-dot.offline { background: var(--accent-red); }
.source-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.availability { font-size: 12px; color: var(--text-secondary); }
.source-detail { font-size: 11px; color: var(--text-muted); }
</style>
