<script setup lang="ts">
// KPI 卡：顶部 2px 态色条 + label(mono) + 大数字(Space Grotesk 26–38px) + sub。
import { computed } from 'vue'
import type { DotState } from '../types'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  sub?: string
  state?: DotState | 'accent'
}>(), { state: 'accent' })

const barColor = computed(() =>
  props.state === 'accent' ? 'var(--accent)' : `var(--${props.state}-dot)`,
)
</script>

<template>
  <div class="kpi">
    <div class="bar" :style="{ background: barColor }" />
    <div class="label mono">{{ label }}</div>
    <div class="value num">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </div>
</template>

<style scoped>
.kpi {
  position: relative; background: var(--bg-panel); border: 1px solid var(--bd-panel);
  border-radius: var(--r-card); padding: 14px 15px 13px; overflow: hidden; min-width: 0;
}
.bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
.label {
  font-size: 10.5px; letter-spacing: .3px; text-transform: uppercase;
  color: var(--tx-muted); margin-bottom: 7px;
}
.value { font-size: 30px; font-weight: 600; letter-spacing: -.5px; color: var(--tx-1); line-height: 1; }
.sub { margin-top: 7px; font-size: 11.5px; color: var(--tx-4); }
</style>
