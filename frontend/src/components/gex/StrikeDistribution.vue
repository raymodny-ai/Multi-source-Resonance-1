<template>
  <div class="strike-distribution">
    <BarChart
      :x-data="xData"
      :series="chartSeries"
      :height="height"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BarChart from '@/components/charts/BarChart.vue'
import type { GEXStrike } from '@/api/gex'

const props = defineProps<{
  strikes: GEXStrike[]
  height?: number
}>()

const xData = computed(() => props.strikes.map((s) => s.strike.toFixed(0)))

const chartSeries = computed(() => [
  { name: 'Call GEX', data: props.strikes.map((s) => s.call_gex), color: '#22d3ee', stack: 'gex' },
  { name: 'Put GEX', data: props.strikes.map((s) => s.put_gex), color: '#ef4444', stack: 'gex' },
])
</script>
