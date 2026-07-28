<template>
  <v-chart :option="chartOption" autoresize :style="{ width: '100%', height: height + 'px' }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const props = defineProps<{
  xData: string[]
  series: { name: string; data: number[]; color?: string; stack?: string }[]
  height?: number
  horizontal?: boolean
}>()

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(17,17,40,0.9)',
    borderColor: 'rgba(255,255,255,0.1)',
    textStyle: { color: '#f0f0f5' },
  },
  legend: {
    data: props.series.map((s) => s.name),
    textStyle: { color: '#a0a0b5' },
  },
  grid: { left: 60, right: 20, top: 40, bottom: 30 },
  xAxis: props.horizontal
    ? { type: 'value', axisLabel: { color: '#6b6b80' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } }
    : { type: 'category', data: props.xData, axisLabel: { color: '#6b6b80', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
  yAxis: props.horizontal
    ? { type: 'category', data: props.xData, axisLabel: { color: '#6b6b80' } }
    : { type: 'value', axisLabel: { color: '#6b6b80' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
  series: props.series.map((s, i) => ({
    name: s.name,
    type: 'bar',
    data: s.data,
    stack: s.stack,
    itemStyle: { color: s.color || ['#6366f1', '#22d3ee', '#ef4444', '#10b981'][i], borderRadius: s.stack ? undefined : [4, 4, 0, 0] },
  })),
}))
</script>
