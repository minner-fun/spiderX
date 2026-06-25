<script setup lang="ts">
// CTA 按钮：accent 青底辉光 / ghost 描边 / danger 红。
withDefaults(defineProps<{
  variant?: 'accent' | 'ghost' | 'danger'
  type?: 'button' | 'submit'
  disabled?: boolean
}>(), { variant: 'ghost', type: 'button', disabled: false })
defineEmits<{ (e: 'click', ev: MouseEvent): void }>()
</script>

<template>
  <button
    class="cta" :class="variant" :type="type" :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.cta {
  font-family: var(--font-body); font-size: 12.5px; font-weight: 600; line-height: 1;
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 15px; border-radius: var(--r-card); cursor: pointer;
  border: 1px solid transparent; transition: box-shadow .14s, background .14s, border-color .14s, opacity .14s;
}
.cta:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }

.cta.accent {
  background: var(--accent-grad); color: var(--accent-on);
  box-shadow: var(--accent-glow);
}
.cta.accent:hover:not(:disabled) { box-shadow: var(--accent-glow-hover); }

.cta.ghost {
  background: var(--bg-chip); border-color: var(--bd-control); color: var(--tx-2);
}
.cta.ghost:hover:not(:disabled) { border-color: var(--bd-accent); color: var(--tx-1); }

.cta.danger {
  background: var(--red-bg); border-color: var(--red-bd); color: var(--red-text);
}
.cta.danger:hover:not(:disabled) { border-color: var(--red-dot); }
</style>
