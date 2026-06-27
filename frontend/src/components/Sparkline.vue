<script setup lang="ts">
// 迷你 sparkline（ECharts line+area，无轴）。态色描边，末点断崖时高亮。
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { DotState } from '../types'

echarts.use([LineChart, GridComponent, CanvasRenderer])

const props = withDefaults(defineProps<{ values: number[]; state?: DotState; w?: number; h?: number }>(), {
  state: 'cyan', w: 96, h: 26,
})

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function color() {
  const map: Record<string, string> = {
    red: '--red-dot', yellow: '--yellow-dot', green: '--green-dot',
    unknown: '--unknown-dot', cyan: '--accent',
  }
  return getComputedStyle(document.documentElement).getPropertyValue(map[props.state] || '--accent').trim() || '#4cc9e0'
}

function render() {
  if (!chart) return
  const c = color()
  chart.setOption({
    grid: { left: 1, right: 1, top: 2, bottom: 2 },
    xAxis: { type: 'category', show: false, boundaryGap: false },
    yAxis: { type: 'value', show: false, scale: true },
    series: [{
      type: 'line', data: props.values, smooth: true, symbol: 'none',
      lineStyle: { color: c, width: 1.5 },
      areaStyle: { color: c, opacity: 0.12 },
    }],
  })
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value, undefined, { renderer: 'canvas', width: props.w, height: props.h })
  render()
})
onBeforeUnmount(() => chart?.dispose())
watch(() => [props.values, props.state], render, { deep: true })
</script>

<template>
  <div ref="el" class="spark" :style="{ width: w + 'px', height: h + 'px' }" />
</template>

<style scoped>.spark { flex: none; }</style>
