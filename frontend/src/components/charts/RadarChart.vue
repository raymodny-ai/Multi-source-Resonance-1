<template>
  <v-chart :option="chartOption" autoresize :style="{ width: '100%', height: height + 'px' }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([RadarChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  dimensions: { gex: number; vix: number; crypto: number; darkpool: number }
  maxScore?: number
  height?: number
}>()

const chartOption = computed(() => ({
  tooltip: {
    backgroundColor: 'rgba(17,17,40,0.9)',
    borderColor: 'rgba(255,255,255,0.1)',
    textStyle: { color: '#f0f0f5' },
  },
  radar: {
    indicator: [
      { name: 'GEX', max: props.maxScore ?? 2.5 },
      { name: 'VIX', max: props.maxScore ?? 1.5 },
      { name: 'Crypto', max: props.maxScore ?? 2.0 },
      { name: 'Darkpool', max: props.maxScore ?? 2.0 },
    ],
    shape: 'polygon',
    splitNumber: 4,
    axisName: { color: '#a0a0b5', fontSize: 12 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    splitArea: { areaStyle: { color: ['rgba(99,102,241,0.02)', 'rgba(99,102,241,0.05)'] } },
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [props.dimensions.gex, props.dimensions.vix, props.dimensions.crypto, props.dimensions.darkpool],
      name: '共振评分',
      areaStyle: { color: 'rgba(99,102,241,0.2)' },
      lineStyle: { color: '#6366f1', width: 2 },
      itemStyle: { color: '#6366f1' },
    }],
  }],
}))
</script>
