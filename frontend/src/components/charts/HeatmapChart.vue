<template>
  <v-chart :option="chartOption" autoresize :style="{ width: '100%', height: height + 'px' }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { HeatmapChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([HeatmapChart, TooltipComponent, GridComponent, VisualMapComponent, CanvasRenderer])

const props = defineProps<{
  xLabels: string[]
  yLabels: string[]
  data: [number, number, number][]
  height?: number
}>()

const chartOption = computed(() => ({
  tooltip: {
    backgroundColor: 'rgba(17,17,40,0.9)',
    borderColor: 'rgba(255,255,255,0.1)',
    textStyle: { color: '#f0f0f5' },
  },
  grid: { left: 80, right: 40, top: 10, bottom: 40 },
  xAxis: {
    type: 'category',
    data: props.xLabels,
    axisLabel: { color: '#a0a0b5' },
    splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
  },
  yAxis: {
    type: 'category',
    data: props.yLabels,
    axisLabel: { color: '#a0a0b5' },
  },
  visualMap: {
    min: 0,
    max: 1,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: 0,
    inRange: { color: ['#1a1a3e', '#6366f1', '#22d3ee'] },
    textStyle: { color: '#a0a0b5' },
  },
  series: [{
    type: 'heatmap',
    data: props.data,
    label: { show: true, color: '#f0f0f5', fontSize: 11 },
    itemStyle: { borderColor: '#0a0a1a', borderWidth: 2 },
  }],
}))
</script>
