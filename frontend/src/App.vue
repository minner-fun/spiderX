<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const nav = [
  { label: '巡检分诊', to: '/triage', icon: '◎' },
]
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="logo">🕷 <b>Arachne</b></div>
      <nav>
        <RouterLink v-for="n in nav" :key="n.to" :to="n.to"
          class="navitem" :class="{ active: route.path === n.to }">
          <span class="ico">{{ n.icon }}</span>{{ n.label }}
        </RouterLink>
      </nav>
      <div class="foot">ops@team · M0</div>
    </aside>
    <main class="main">
      <header class="topbar">
        <span class="proj">项目：demo-招投标</span>
        <span class="env">env: dev</span>
        <span class="grow" />
        <span class="badge">SpiderX 控制台</span>
      </header>
      <section class="content"><RouterView /></section>
    </main>
  </div>
</template>

<style scoped>
.shell { display: flex; height: 100%; }
.sidebar { width: 200px; background: var(--panel); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; padding: 14px 10px; gap: 4px; }
.logo { font-size: 18px; padding: 6px 8px 16px; }
.navitem { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 6px;
  color: var(--muted); border-left: 3px solid transparent; }
.navitem.active { background: var(--panel-2); color: var(--text); border-left-color: var(--accent); font-weight: 600; }
.ico { width: 16px; text-align: center; }
.foot { margin-top: auto; color: var(--muted); font-size: 12px; padding: 8px; border-top: 1px solid var(--border); }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar { height: 52px; border-bottom: 1px solid var(--border); display: flex; align-items: center;
  gap: 12px; padding: 0 16px; background: var(--panel); }
.proj, .env { font-size: 13px; color: var(--muted); border: 1px solid var(--border);
  border-radius: 6px; padding: 5px 10px; }
.grow { flex: 1; }
.badge { font-size: 12px; color: var(--accent); }
.content { flex: 1; overflow: auto; padding: 18px; }
</style>
