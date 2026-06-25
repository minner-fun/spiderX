<script setup lang="ts">
// 通用状态灯：8px 圆点 + box-shadow 辉光；live 加 hfpulse 呼吸。
import { computed } from 'vue'
import type { DotState } from '../types'

const props = withDefaults(defineProps<{ state: DotState; live?: boolean; size?: number }>(), {
  live: false,
  size: 8,
})

const color = computed(() => `var(--${props.state}-dot)`)
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  background: color.value,
  boxShadow: `0 0 8px ${color.value}`,
}))
</script>

<template>
  <span class="hf-dot" :class="{ live }" :style="style" />
</template>

<style scoped>
.hf-dot { border-radius: 50%; display: inline-block; flex: none; }
.hf-dot.live { animation: hfpulse 1.5s infinite; }
</style>
