<script setup lang="ts">
// 执行态徽章：running 绿脉冲 / paused 灰 / failed 红 / disabled 弱。
// 注意：执行态与健康态分离 —— 这里用执行语义，不复用健康三态色含义。
import { computed } from 'vue'
import type { ExecStatus, DotState } from '../types'
import { EXEC_LABEL } from '../types'
import StatusDot from './StatusDot.vue'

const props = defineProps<{ status: ExecStatus }>()

const map: Record<ExecStatus, { dot: DotState; live: boolean }> = {
  running: { dot: 'green', live: true },
  paused: { dot: 'unknown', live: false },
  failed: { dot: 'red', live: false },
  disabled: { dot: 'unknown', live: false },
}

const cfg = computed(() => map[props.status])
const label = computed(() => EXEC_LABEL[props.status])
</script>

<template>
  <span class="exec" :class="status">
    <StatusDot :state="cfg.dot" :live="cfg.live" :size="6" />
    {{ label }}
  </span>
</template>

<style scoped>
.exec {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 9px; border: 1px solid var(--bd-control); border-radius: var(--r-badge);
  font-size: 11.5px; font-weight: 500; color: var(--tx-3);
  background: var(--bg-chip); white-space: nowrap; line-height: 1.2;
}
.exec.running { color: var(--green-text); border-color: var(--green-bd); background: var(--green-bg); }
.exec.failed { color: var(--red-text); border-color: var(--red-bd); background: var(--red-bg); }
.exec.disabled { color: var(--tx-weak); opacity: .75; }
</style>
