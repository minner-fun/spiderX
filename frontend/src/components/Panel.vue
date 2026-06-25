<script setup lang="ts">
// 面板容器：--bg-panel + --bd-panel + --r-panel。可选标题行 + 右侧 mono 副标题。
defineProps<{ title?: string; subtitle?: string; pad?: boolean }>()
</script>

<template>
  <section class="panel">
    <header v-if="title || subtitle || $slots.actions" class="phead">
      <span class="ptitle">{{ title }}</span>
      <span class="grow" />
      <span v-if="subtitle" class="psub mono">{{ subtitle }}</span>
      <slot name="actions" />
    </header>
    <div class="pbody" :class="{ pad: pad !== false }">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: var(--bg-panel); border: 1px solid var(--bd-panel);
  border-radius: var(--r-panel); overflow: hidden;
}
.phead {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 15px; border-bottom: 1px solid var(--bd-divider);
}
.ptitle { font-family: var(--font-head); font-weight: 600; font-size: 13px; color: var(--tx-strong); }
.grow { flex: 1; }
.psub { font-size: 11px; color: var(--tx-muted); }
.pbody.pad { padding: 15px; }
</style>
