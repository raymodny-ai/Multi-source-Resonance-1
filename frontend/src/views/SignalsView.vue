<template>
  <div class="signals-view">
    <div class="view-header">
      <h3 class="section-title">信号历史</h3>
      <div class="header-actions">
        <span class="total-count">共 {{ signalStore.totalSignals }} 条信号</span>
      </div>
    </div>

    <div class="glass-card">
      <SignalTable :signals="signalStore.signalHistory" @acknowledge="handleAck" />
    </div>

    <div class="pagination" v-if="signalStore.totalSignals > pageSize">
      <button class="page-btn" :disabled="currentPage === 0" @click="changePage(-1)">上一页</button>
      <span class="page-info">第 {{ currentPage + 1 }} 页</span>
      <button class="page-btn" :disabled="(currentPage + 1) * pageSize >= signalStore.totalSignals" @click="changePage(1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSignalStore } from '@/stores/signals'
import SignalTable from '@/components/signals/SignalTable.vue'

const signalStore = useSignalStore()
const currentPage = ref(0)
const pageSize = 50

function handleAck(id: number) {
  signalStore.acknowledge(id)
}

function changePage(delta: number) {
  currentPage.value += delta
  signalStore.fetchSignalHistory(currentPage.value * pageSize, pageSize)
}

onMounted(() => {
  signalStore.fetchSignalHistory(0, pageSize)
})
</script>

<style scoped>
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-lg); }
.section-title { font-size: 16px; font-weight: 600; }
.total-count { font-size: 13px; color: var(--text-muted); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: var(--spacing-lg); }
.page-btn { background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-secondary); padding: 6px 16px; border-radius: 8px; cursor: pointer; }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-info { font-size: 13px; color: var(--text-muted); }
</style>
