<template>
  <div class="source-card glass-card" :class="{ 'has-error': hasError, 'is-mock': source.is_mock }">
    <div class="source-header">
      <span class="source-name">{{ source.name }}</span>
      <span class="status-dot" :class="source.status"></span>
    </div>
    <div class="source-meta">
      <span :class="'badge badge-' + statusBadgeClass">{{ source.status.toUpperCase() }}</span>
      <span
        v-if="source.is_mock"
        class="badge badge-mock"
        :title="mockReasonText"
      >MOCK</span>
      <span class="availability" v-if="source.availability_pct != null">
        {{ source.availability_pct.toFixed(0) }}%
      </span>
    </div>
    <div class="source-detail" v-if="source.age_minutes != null">
      延迟: {{ formatAge(source.age_minutes) }}
    </div>
    <div
      v-if="source.is_mock && source.mock_reason"
      class="source-detail source-mock-reason"
    >
      原因: {{ mockReasonText }}
      <span v-if="source.retry_count" class="source-retry">
        (重试 {{ source.retry_count }})
      </span>
    </div>
    <div
      v-if="source.last_error"
      class="source-error"
      :title="source.last_error"
    >
      <span class="source-error-icon">❗</span>
      <span class="source-error-text">{{ truncate(source.last_error, 60) }}</span>
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

const hasError = computed(() => !!props.source.last_error)

const mockReasonText = computed(() => {
  const reason = props.source.mock_reason
  if (!reason) return ''
  // Map backend reason codes to a human-readable Chinese phrase.
  const map: Record<string, string> = {
    api_key_absent: 'API 密钥缺失',
    fetch_failed_fallback: '数据获取失败',
    internal_fallback: '内部降级',
  }
  return map[reason] || reason
})

function truncate(text: string, max: number): string {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '…' : text
}

function formatAge(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)}h`
  return `${(minutes / 1440).toFixed(1)}d`
}
</script>

<style scoped>
.source-card { padding: var(--spacing-md); transition: border-color 0.2s; }
.source-card.has-error { border-color: rgba(239, 68, 68, 0.6); }
.source-card.is-mock { border-color: rgba(245, 158, 11, 0.5); }
.source-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.source-name { font-size: 13px; font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.online { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
.status-dot.degraded { background: var(--accent-amber); }
.status-dot.offline { background: var(--accent-red); }
.source-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.availability { font-size: 12px; color: var(--text-secondary); }
.source-detail { font-size: 11px; color: var(--text-muted); }
.source-mock-reason { color: var(--accent-amber); }
.source-retry { color: var(--text-muted); margin-left: 4px; }
.badge-mock {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-amber);
  border: 1px solid rgba(245, 158, 11, 0.4);
}
.source-error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 6px;
  color: var(--accent-red);
  font-size: 11px;
  line-height: 1.4;
}
.source-error-icon { font-size: 13px; line-height: 1; }
.source-error-text { flex: 1; word-break: break-all; }
</style>

