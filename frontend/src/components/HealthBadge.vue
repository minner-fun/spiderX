<script setup lang="ts">
// 健康三态徽章：点 + 文字 + 暗底 + 暗边，色取 --{state}-*。含 unknown ⚪。
import { computed } from 'vue'
import StatusDot from './StatusDot.vue'
import type { HealthStatus } from '../types'
import { HEALTH_TO_DOT, HEALTH_LABEL } from '../types'

const props = defineProps<{ status: HealthStatus }>()

const dot = computed(() => HEALTH_TO_DOT[props.status])
const label = computed(() => HEALTH_LABEL[props.status])
const style = computed(() => ({
  background: `var(--${dot.value}-bg)`,
  borderColor: `var(--${dot.value}-bd)`,
  color: `var(--${dot.value}-text)`,
}))
</script>

<template>
  <span class="badge" :style="style">
    <StatusDot :state="dot" :size="7" />
    {{ label }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 9px; border: 1px solid; border-radius: var(--r-badge);
  font-size: 11.5px; font-weight: 500; white-space: nowrap; line-height: 1.2;
}
</style>
