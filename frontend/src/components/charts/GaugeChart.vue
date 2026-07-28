<template>
  <v-chart :option="chartOption" autoresize :style="{ width: '100%', height: height + 'px' }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { GaugeChart } from 'echarts/charts'
import { TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([GaugeChart, TitleComponent, CanvasRenderer])

const props = defineProps<{
  value: number
  max?: number
  title?: string
  height?: number
}>()

const chartOption = computed(() => ({
  series: [{
    type: 'gauge',
    startAngle: 200,
    endAngle: -20,
    min: 0,
    max: props.max ?? 5.0,
    splitNumber: 5,
    radius: '90%',
    axisLine: {
      lineStyle: {
        width: 20,
        color: [
          [0.4, '#ef4444'],
          [0.6, '#f59e0b'],
          [0.7, '#22d3ee'],
          [1, '#10b981'],
        ],
      },
    },
    pointer: {
      itemStyle: { color: '#f0f0f5' },
      width: 4,
    },
    axisTick: { distance: -20, length: 6, lineStyle: { color: 'rgba(255,255,255,0.2)' } },
    splitLine: { distance: -24, length: 20, lineStyle: { color: 'rgba(255,255,255,0.2)', width: 2 } },
    axisLabel: { color: '#6b6b80', distance: 30, fontSize: 11 },
    detail: {
      valueAnimation: true,
      formatter: '{value}',
      color: '#f0f0f5',
      fontSize: 24,
      fontWeight: 'bold',
      offsetCenter: [0, '60%'],
    },
    title: {
      offsetCenter: [0, '85%'],
      fontSize: 12,
      color: '#a0a0b5',
    },
    data: [{
      value: props.value,
      name: props.title || 'Score',
    }],
  }],
}))
</script>
