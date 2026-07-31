<template>
  <div v-if="visibleToasts.length" class="error-toast-container" role="status" aria-live="polite">
    <div
      v-for="t in visibleToasts"
      :key="t.id"
      class="error-toast"
      :class="'toast-' + t.level"
    >
      <span class="error-toast-icon">{{ iconFor(t.level) }}</span>
      <div class="error-toast-body">
        <div class="error-toast-title">{{ t.title }}</div>
        <div v-if="t.message" class="error-toast-message">{{ t.message }}</div>
      </div>
      <button
        class="error-toast-close"
        type="button"
        aria-label="关闭"
        @click="dismiss(t.id)"
      >×</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface ToastItem {
  id: number
  title: string
  message: string
  level: 'info' | 'warning' | 'error' | 'success'
  expires_at: number
}

const MAX_VISIBLE = 3
const TTL_MS = 5000
const toasts = ref<ToastItem[]>([])
let nextId = 1
let pruneTimer: ReturnType<typeof setInterval> | null = null

const visibleToasts = computed(() => toasts.value.slice(0, MAX_VISIBLE))

function iconFor(level: ToastItem['level']): string {
  if (level === 'error') return '❗'
  if (level === 'warning') return '⚠'
  if (level === 'success') return '✓'
  return 'ℹ'
}

function levelFromStatus(status?: number): ToastItem['level'] {
  if (!status) return 'error'
  if (status >= 500) return 'error'
  if (status >= 400) return 'warning'
  return 'info'
}

function pushToast(item: Omit<ToastItem, 'id' | 'expires_at'>) {
  const toast: ToastItem = {
    id: nextId++,
    expires_at: Date.now() + TTL_MS,
    ...item,
  }
  toasts.value = [toast, ...toasts.value].slice(0, MAX_VISIBLE)
}

function dismiss(id: number) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function onApiError(ev: Event) {
  const detail = (ev as CustomEvent).detail as
    | { url?: string; status?: number; message?: string }
    | undefined
  if (!detail) return
  const status = detail.status
  // 401s are already handled by the auth refresh flow; don't double-toast.
  if (status === 401) return
  pushToast({
    title: status ? `请求失败 (${status})` : '网络错误',
    message: detail.message || detail.url || '请稍后重试',
    level: levelFromStatus(status),
  })
}

function onWsStatus(ev: Event) {
  const detail = (ev as CustomEvent).detail as { connected?: boolean } | undefined
  if (!detail) return
  if (detail.connected) {
    pushToast({ title: '实时连接已恢复', message: 'WebSocket 重新连上', level: 'success' })
  } else {
    pushToast({
      title: '实时连接已断开',
      message: '正在尝试重连...',
      level: 'warning',
    })
  }
}

function prune() {
  const now = Date.now()
  toasts.value = toasts.value.filter((t) => t.expires_at > now)
}

onMounted(() => {
  window.addEventListener('msr-api-error', onApiError)
  window.addEventListener('msr-ws-status', onWsStatus)
  pruneTimer = setInterval(prune, 1000)
})

onUnmounted(() => {
  window.removeEventListener('msr-api-error', onApiError)
  window.removeEventListener('msr-ws-status', onWsStatus)
  if (pruneTimer) {
    clearInterval(pruneTimer)
    pruneTimer = null
  }
})
</script>

<style scoped>
.error-toast-container {
  position: fixed;
  right: 16px;
  bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10000;
  max-width: 360px;
  pointer-events: none;
}
.error-toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(17, 17, 40, 0.95);
  border: 1px solid rgba(239, 68, 68, 0.5);
  border-left-width: 4px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  color: var(--text-primary);
  font-size: 13px;
  pointer-events: auto;
  backdrop-filter: blur(8px);
}
.error-toast.toast-info { border-color: rgba(99, 102, 241, 0.5); }
.error-toast.toast-warning { border-color: rgba(245, 158, 11, 0.6); }
.error-toast.toast-error { border-color: rgba(239, 68, 68, 0.7); }
.error-toast.toast-success { border-color: rgba(16, 185, 129, 0.6); }
.error-toast-icon { font-size: 16px; line-height: 1.2; }
.error-toast-body { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.error-toast-title { font-weight: 600; }
.error-toast-message { font-size: 12px; color: var(--text-secondary); word-break: break-all; }
.error-toast-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 4px;
}
.error-toast-close:hover { color: var(--text-primary); background: rgba(255, 255, 255, 0.05); }
</style>
