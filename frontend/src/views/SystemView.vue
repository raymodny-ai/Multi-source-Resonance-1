<template>
  <div class="system-view">
    <div class="system-grid">
      <!-- System Status -->
      <div class="glass-card">
        <h3 class="section-title">系统状态</h3>
        <div v-if="systemStore.systemStatus" class="status-grid">
          <div class="status-item"><span class="status-label">CPU</span><span class="status-val">{{ systemStore.systemStatus.cpu_percent }}%</span></div>
          <div class="status-item"><span class="status-label">内存</span><span class="status-val">{{ systemStore.systemStatus.memory_percent }}%</span></div>
          <div class="status-item"><span class="status-label">DB 大小</span><span class="status-val">{{ systemStore.systemStatus.db_size_mb }} MB</span></div>
          <div class="status-item"><span class="status-label">Uptime</span><span class="status-val">{{ systemStore.uptimeFormatted }}</span></div>
          <div class="status-item"><span class="status-label">Python</span><span class="status-val">{{ systemStore.systemStatus.python_version }}</span></div>
        </div>
      </div>

      <!-- Source Status -->
      <div class="glass-card">
        <h3 class="section-title">数据源状态</h3>
        <div class="source-list">
          <SourceStatusCard v-for="src in systemStore.sourceStatuses" :key="src.name" :source="src" />
        </div>
      </div>

      <!-- Pipeline Control -->
      <div class="glass-card">
        <h3 class="section-title">Pipeline 控制</h3>
        <div class="pipeline-controls">
          <div class="control-row">
            <span>自动轮询</span>
            <span class="badge" :class="systemStore.autoPolling?.enabled ? 'badge-green' : 'badge-red'">
              {{ systemStore.autoPolling?.enabled ? '运行中' : '已停止' }}
            </span>
          </div>
          <div class="btn-group">
            <button class="ctrl-btn" @click="systemStore.toggleAutoPolling(!systemStore.autoPolling?.enabled)">
              {{ systemStore.autoPolling?.enabled ? '停止' : '启动' }}
            </button>
            <button class="ctrl-btn primary" @click="systemStore.collectManual()" :disabled="systemStore.collecting">
              {{ systemStore.collecting ? '采集中...' : '手动采集' }}
            </button>
          </div>
        </div>
      </div>

      <!-- System Logs -->
      <div class="glass-card logs-card">
        <h3 class="section-title">系统日志</h3>
        <div class="log-list">
          <div v-for="(log, i) in systemStore.systemLogs" :key="i" class="log-entry" :class="'log-' + log.level?.toLowerCase()">
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-source">[{{ log.source }}]</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
          <div v-if="systemStore.systemLogs.length === 0" class="no-data">暂无日志</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import SourceStatusCard from '@/components/dashboard/SourceStatusCard.vue'

const systemStore = useSystemStore()

function formatTime(ts: string): string {
  try { return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) } catch { return ts }
}

onMounted(() => {
  systemStore.fetchSystemStatus()
  systemStore.fetchSourceStatus()
  systemStore.fetchAutoPolling()
  systemStore.fetchLogs(100)
})
</script>

<style scoped>
.system-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.status-grid { display: flex; flex-direction: column; gap: 8px; }
.status-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.status-label { font-size: 13px; color: var(--text-muted); }
.status-val { font-size: 14px; font-weight: 600; }
.source-list { display: flex; flex-direction: column; gap: 8px; }
.pipeline-controls { display: flex; flex-direction: column; gap: 12px; }
.control-row { display: flex; justify-content: space-between; align-items: center; }
.btn-group { display: flex; gap: 8px; }
.ctrl-btn { background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.ctrl-btn:hover { background: rgba(99,102,241,0.1); }
.ctrl-btn.primary { background: rgba(99,102,241,0.2); color: var(--accent-indigo); border-color: var(--accent-indigo); }
.ctrl-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.logs-card { grid-column: 1 / -1; }
.log-list { max-height: 300px; overflow-y: auto; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; }
.log-entry { display: flex; gap: 8px; padding: 3px 0; }
.log-time { color: var(--text-muted); white-space: nowrap; }
.log-source { color: var(--accent-cyan); white-space: nowrap; }
.log-msg { color: var(--text-secondary); }
.log-error .log-msg { color: var(--accent-red); }
.log-warn .log-msg { color: var(--accent-amber); }
.no-data { text-align: center; color: var(--text-muted); padding: 24px; }
</style>
