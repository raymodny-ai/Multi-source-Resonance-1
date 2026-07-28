<template>
  <header class="header">
    <div class="header-left">
      <h2 class="page-title">{{ currentTitle }}</h2>
    </div>
    <div class="header-right">
      <div class="ws-status" :class="{ connected: wsConnected }">
        <span class="ws-dot"></span>
        {{ wsConnected ? '实时连接' : '未连接' }}
      </div>
      <div class="last-update" v-if="lastUpdated">
        更新: {{ formatTime(lastUpdated) }}
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useMarketStore } from '@/stores/market'

const route = useRoute()
const marketStore = useMarketStore()

const currentTitle = computed(() => (route.meta.title as string) || 'Monitor')
const lastUpdated = computed(() => marketStore.lastUpdated)
const wsConnected = computed(() => false) // Updated by WebSocket composable

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}
</script>

<style scoped>
.header {
  height: var(--header-height);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  flex-shrink: 0;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}
.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-red);
}
.ws-status.connected .ws-dot {
  background: var(--accent-green);
  box-shadow: 0 0 6px var(--accent-green);
}
.last-update {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
