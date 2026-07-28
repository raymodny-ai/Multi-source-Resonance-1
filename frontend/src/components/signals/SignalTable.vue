<template>
  <div class="signal-table-wrapper">
    <table class="signal-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>级别</th>
          <th>总分</th>
          <th>GEX</th>
          <th>VIX</th>
          <th>Crypto</th>
          <th>Darkpool</th>
          <th>Hawkes</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="signal in signals" :key="signal.id">
          <td>{{ formatTime(signal.trigger_time) }}</td>
          <td><span class="badge" :class="'badge-' + levelBadge(signal.alert_level)">{{ signal.alert_level }}</span></td>
          <td class="score-cell">{{ signal.total_score.toFixed(2) }}</td>
          <td>{{ signal.gex_score?.toFixed(2) ?? '—' }}</td>
          <td>{{ signal.vix_score?.toFixed(2) ?? '—' }}</td>
          <td>{{ signal.crypto_score?.toFixed(2) ?? '—' }}</td>
          <td>{{ signal.darkpool_score?.toFixed(2) ?? '—' }}</td>
          <td>{{ signal.hawkes_branching_ratio?.toFixed(3) ?? '—' }}</td>
          <td>
            <span :class="signal.acknowledged ? 'text-muted' : 'text-amber'">
              {{ signal.acknowledged ? '已确认' : '待处理' }}
            </span>
          </td>
          <td>
            <button v-if="!signal.acknowledged" class="btn-ack" @click="$emit('acknowledge', signal.id)">确认</button>
          </td>
        </tr>
        <tr v-if="signals.length === 0">
          <td colspan="10" class="empty">暂无信号数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { SignalAlert } from '@/api/signals'

defineProps<{ signals: SignalAlert[] }>()
defineEmits<{ acknowledge: [id: number] }>()

function formatTime(ts: string): string {
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}

function levelBadge(level: string): string {
  if (level === 'LEVEL_3') return 'red'
  if (level === 'LEVEL_2') return 'amber'
  return 'indigo'
}
</script>

<style scoped>
.signal-table-wrapper { overflow-x: auto; }
.signal-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.signal-table th { text-align: left; padding: 10px 12px; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--glass-border); font-size: 11px; text-transform: uppercase; }
.signal-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
.signal-table tr:hover { background: var(--glass-bg); }
.score-cell { font-weight: 700; }
.btn-ack { background: rgba(99,102,241,0.2); color: var(--accent-indigo); border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.btn-ack:hover { background: rgba(99,102,241,0.3); }
.empty { text-align: center; color: var(--text-muted); padding: 32px; }
</style>
