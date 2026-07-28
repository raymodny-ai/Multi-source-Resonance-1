<template>
  <div class="gex-curve">
    <LineChart
      :x-data="xData"
      :series="chartSeries"
      :height="height"
      :title="title"
      :area-style="true"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LineChart from '@/components/charts/LineChart.vue'

const props = defineProps<{
  data: { timestamp: string; net_gex: number; spot_price?: number }[]
  height?: number
  title?: string
}>()

const xData = computed(() =>
  props.data.map((d) => {
    try { return new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) } catch { return d.timestamp }
  })
)

const chartSeries = computed(() => [
  { name: 'Net GEX', data: props.data.map((d) => d.net_gex), color: '#6366f1' },
])
</script>
