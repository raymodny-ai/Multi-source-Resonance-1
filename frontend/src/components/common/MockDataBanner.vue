<template>
  <div v-if="modelValue" class="mock-banner" role="status">
    <span class="mock-banner-icon">⚠</span>
    <div class="mock-banner-text">
      <strong>{{ title }}</strong>
      <span class="mock-banner-detail">
        <span v-if="sources && sources.length">
          {{ sourcesLabel }}
        </span>
        <slot name="detail" />
      </span>
    </div>
    <button
      v-if="dismissible"
      class="mock-banner-close"
      type="button"
      aria-label="关闭"
      @click="close"
    >×</button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    sources?: string[] | null
    title?: string
    dismissible?: boolean
  }>(),
  {
    sources: () => [],
    title: '当前数据包含模拟值',
    dismissible: true,
  },
)

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
const internal = ref(true)
const modelValue = computed({
  get: () => internal.value,
  set: (v: boolean) => {
    internal.value = v
    emit('update:modelValue', v)
  },
})

const sourcesLabel = computed(() => {
  if (!props.sources?.length) return ''
  return `来源: ${props.sources.join('、')}`
})

function close() {
  modelValue.value = false
}
</script>

<style scoped>
.mock-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: var(--spacing-md);
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.5);
  border-left-width: 4px;
  border-radius: 8px;
  color: var(--accent-amber);
  font-size: 13px;
}
.mock-banner-icon { font-size: 18px; line-height: 1; }
.mock-banner-text { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.mock-banner-detail { font-size: 12px; color: var(--text-secondary); font-weight: 400; }
.mock-banner-close {
  background: transparent;
  border: none;
  color: var(--accent-amber);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 4px;
}
.mock-banner-close:hover { background: rgba(245, 158, 11, 0.15); }
</style>
