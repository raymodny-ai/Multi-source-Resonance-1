<template>
  <footer class="footer">
    <span>Multi-source Resonance Monitor v3.1</span>
    <span class="footer-right">
      <span v-if="dbSize">DB: {{ dbSize }} MB</span>
      <span v-if="uptime">Uptime: {{ uptime }}</span>
    </span>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
const dbSize = computed(() => systemStore.systemStatus?.db_size_mb?.toFixed(1))
const uptime = computed(() => systemStore.uptimeFormatted)
</script>

<style scoped>
.footer {
  height: var(--footer-height);
  background: var(--bg-secondary);
  border-top: 1px solid var(--glass-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.footer-right {
  display: flex;
  gap: var(--spacing-md);
}
</style>
