<template>
  <v-chart :option="chartOption" autoresize :style="{ width: '100%', height: height + 'px' }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const props = defineProps<{
  xData: string[]
  series: { name: string; data: number[]; color?: string }[]
  height?: number
  title?: string
  areaStyle?: boolean
}>()

const chartOption = computed(() => ({
  title: props.title ? { text: props.title, textStyle: { color: '#f0f0f5', fontSize: 14 }, left: 'left' } : undefined,
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(17,17,40,0.9)',
    borderColor: 'rgba(255,255,255,0.1)',
    textStyle: { color: '#f0f0f5' },
  },
  legend: {
    data: props.series.map((s) => s.name),
    textStyle: { color: '#a0a0b5' },
    top: props.title ? 30 : 0,
  },
  grid: { left: 60, right: 20, top: props.title ? 60 : 40, bottom: 30 },
  xAxis: {
    type: 'category',
    data: props.xData,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    axisLabel: { color: '#6b6b80', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    axisLabel: { color: '#6b6b80', fontSize: 11 },
  },
  series: props.series.map((s, i) => ({
    name: s.name,
    type: 'line',
    data: s.data,
    smooth: true,
    lineStyle: { color: s.color || ['#6366f1', '#22d3ee', '#10b981', '#f59e0b'][i], width: 2 },
    itemStyle: { color: s.color || ['#6366f1', '#22d3ee', '#10b981', '#f59e0b'][i] },
    areaStyle: props.areaStyle ? { opacity: 0.15 } : undefined,
    symbol: 'none',
  })),
}))
</script>
