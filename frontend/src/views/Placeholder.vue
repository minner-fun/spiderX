<script setup lang="ts">
// 未实装屏占位（M2~M4）。保持控制台气质，明确标注里程碑。
import { useRoute } from 'vue-router'
import { computed } from 'vue'
const route = useRoute()
const title = computed(() => (route.meta.title as string) || '待实装')
const ms = computed(() => (route.meta.milestone as string) || '')
</script>

<template>
  <div class="ph">
    <div class="glyph">◷</div>
    <div class="t">{{ title }}</div>
    <div class="m mono" v-if="ms">规划于 {{ ms }} · 暂未实装</div>
    <p class="d">M1 聚焦爬虫主线（列表 → 详情 → 版本）。本屏在后续里程碑落地。</p>
  </div>
</template>

<style scoped>
.ph {
  height: 100%; min-height: 60vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px; text-align: center;
}
.glyph { font-size: 40px; color: var(--tx-weak); opacity: .6; }
.t { font-family: var(--font-head); font-weight: 600; font-size: 19px; color: var(--tx-2); }
.m {
  font-size: 11.5px; color: var(--accent); border: 1px solid var(--bd-control);
  background: var(--bg-chip); padding: 3px 10px; border-radius: var(--r-pill);
}
.d { max-width: 360px; font-size: 12.5px; color: var(--tx-5); margin: 4px 0 0; }
</style>
