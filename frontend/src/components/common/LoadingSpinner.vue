<template>
  <div class="loading-spinner">
    <div class="spinner"></div>
    <span v-if="text" class="spinner-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text?: string }>()
</script>

<style scoped>
.loading-spinner { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px; gap: 12px; }
.spinner {
  width: 32px; height: 32px; border: 3px solid var(--glass-border);
  border-top-color: var(--accent-indigo); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-text { font-size: 13px; color: var(--text-muted); }
</style>
