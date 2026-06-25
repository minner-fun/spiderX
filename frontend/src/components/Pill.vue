<script setup lang="ts">
// 胶囊筛选：选中青边青底 #0f1c20，未选灰。可点。
defineProps<{ active?: boolean }>()
defineEmits<{ (e: 'click'): void }>()
</script>

<template>
  <button class="pill" :class="{ active }" @click="$emit('click')">
    <slot />
  </button>
</template>

<style scoped>
.pill {
  font-family: var(--font-body); font-size: 12px; line-height: 1;
  padding: 6px 12px; border-radius: var(--r-pill); cursor: pointer;
  border: 1px solid var(--bd-control); background: var(--bg-chip); color: var(--tx-3);
  transition: color .12s, border-color .12s, background .12s;
}
.pill:hover { color: var(--tx-1); border-color: var(--bd-accent); }
.pill.active {
  border-color: var(--accent); background: #0f1c20; color: var(--accent);
}
</style>
