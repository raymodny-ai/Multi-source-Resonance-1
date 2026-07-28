<template>
  <div class="term-structure">
    <LineChart
      :x-data="xData"
      :series="chartSeries"
      :height="height"
      :title="title"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LineChart from '@/components/charts/LineChart.vue'
import type { VIXData } from '@/api/vix'

const props = defineProps<{
  data: VIXData[]
  height?: number
  title?: string
}>()

const xData = computed(() =>
  props.data.map((d) => {
    try { return new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.timestamp }
  })
)

const chartSeries = computed(() => [
  { name: 'VIX Spot', data: props.data.map((d) => d.vix_spot), color: '#ef4444' },
  { name: 'VX1', data: props.data.map((d) => d.vx1), color: '#f59e0b' },
  { name: 'VX2', data: props.data.map((d) => d.vx2), color: '#6366f1' },
])
</script>
