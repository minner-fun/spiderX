<script setup lang="ts">
// 数据量基线趋势柱图（ECharts，深色主题）。末柱断崖时红 + 辉光。
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
// 按需引入，避免全量 echarts 进 bundle
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  labels: string[]
  values: number[]
  cliff?: boolean // 末柱断崖（健康非🟢）→ 末柱红
}>()

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function css(v: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim()
}

function render() {
  if (!chart) return
  const accent = css('--accent') || '#4cc9e0'
  const red = css('--red-dot') || '#ff6f59'
  const grid = css('--bd-divider') || '#1c2431'
  const tx = css('--tx-muted') || '#7c8696'
  const last = props.values.length - 1

  chart.setOption({
    grid: { left: 8, right: 8, top: 14, bottom: 22, containLabel: true },
    xAxis: {
      type: 'category', data: props.labels,
      axisLine: { lineStyle: { color: grid } },
      axisTick: { show: false },
      axisLabel: { color: tx, fontFamily: 'JetBrains Mono', fontSize: 9.5 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: grid, type: 'dashed' } },
      axisLabel: { color: tx, fontFamily: 'JetBrains Mono', fontSize: 9.5 },
    },
    tooltip: { trigger: 'axis', backgroundColor: '#0f141d', borderColor: grid,
      textStyle: { color: '#e8eef6', fontSize: 11 } },
    series: [{
      type: 'bar', data: props.values.map((v, i) => {
        const isCliff = props.cliff && i === last
        return {
          value: v,
          itemStyle: {
            color: isCliff ? red : accent,
            opacity: isCliff ? 1 : 0.55,
            borderRadius: [3, 3, 0, 0],
            shadowColor: isCliff ? red : 'transparent',
            shadowBlur: isCliff ? 14 : 0,
          },
        }
      }),
      barWidth: '58%',
    }],
  })
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value, undefined, { renderer: 'canvas' })
  render()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose() })
function resize() { chart?.resize() }
watch(() => [props.labels, props.values, props.cliff], render, { deep: true })
</script>

<template>
  <div ref="el" class="chart" />
</template>

<style scoped>
.chart { width: 100%; height: 180px; }
</style>
