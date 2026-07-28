<template>
  <div class="signal-timeline">
    <div v-for="signal in signals" :key="signal.id" class="timeline-item">
      <div class="timeline-dot" :class="signal.alert_level.toLowerCase()"></div>
      <div class="timeline-content glass-card">
        <div class="timeline-header">
          <span class="badge" :class="'badge-' + levelBadge(signal.alert_level)">{{ signal.alert_level }}</span>
          <span class="timeline-time">{{ formatTime(signal.trigger_time) }}</span>
        </div>
        <div class="timeline-score">Score: {{ signal.total_score.toFixed(2) }}</div>
      </div>
    </div>
    <div v-if="signals.length === 0" class="empty">暂无信号</div>
  </div>
</template>

<script setup lang="ts">
import type { SignalAlert } from '@/api/signals'

defineProps<{ signals: SignalAlert[] }>()

function formatTime(ts: string): string {
  try { return new Date(ts).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return ts }
}

function levelBadge(level: string): string {
  if (level === 'LEVEL_3') return 'red'
  if (level === 'LEVEL_2') return 'amber'
  return 'indigo'
}
</script>

<style scoped>
.signal-timeline { display: flex; flex-direction: column; gap: 12px; position: relative; padding-left: 20px; }
.signal-timeline::before { content: ''; position: absolute; left: 7px; top: 0; bottom: 0; width: 2px; background: var(--glass-border); }
.timeline-item { position: relative; }
.timeline-dot { position: absolute; left: -17px; top: 12px; width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--bg-primary); }
.timeline-dot.level_3 { background: var(--accent-red); }
.timeline-dot.level_2 { background: var(--accent-amber); }
.timeline-dot.level_1, .timeline-dot.none { background: var(--text-muted); }
.timeline-content { padding: var(--spacing-sm) var(--spacing-md); }
.timeline-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.timeline-time { font-size: 11px; color: var(--text-muted); }
.timeline-score { font-size: 14px; font-weight: 600; }
.empty { text-align: center; color: var(--text-muted); padding: 24px; }
</style>
