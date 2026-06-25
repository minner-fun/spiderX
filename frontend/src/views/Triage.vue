<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { api, asItems } from '../api/client'

const health = ref<{ status: string; db: boolean; redis: boolean } | null>(null)
const projectId = ref<string>('')
const spiders = ref<any[]>([])
const events = ref<string[]>([])
const busy = ref(false)
let ws: WebSocket | null = null

async function refresh() {
  health.value = await api.health()
  const projs = await api.listProjects()
  if (projs.length) {
    projectId.value = projs[0].id
    spiders.value = asItems(await api.listSpiders(projectId.value))
  }
}

// M0 终验：建爬虫 → 触发 run → worker 写 Run + pub-sub → 本页 WS 收到
async function demoMainLink() {
  busy.value = true
  try {
    const sp = await api.createSpider(projectId.value, { name: `demo_${Date.now()}` })
    await api.runSpider(sp.id)
    spiders.value = asItems(await api.listSpiders(projectId.value))
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  refresh()
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/triage`)
  ws.onmessage = (e) => events.value.unshift(e.data)
})
onUnmounted(() => ws?.close())
</script>

<template>
  <div class="wrap">
    <h2>巡检分诊 <small>M0 骨架 · 主链路自检</small></h2>

    <div class="cards">
      <div class="card"><div class="lbl">系统健康</div>
        <div class="big" :style="{ color: health?.status === 'ok' ? 'var(--green)' : 'var(--red)' }">
          {{ health?.status ?? '...' }}</div>
        <div class="sub">db {{ health?.db ? '✓' : '✗' }} · redis {{ health?.redis ? '✓' : '✗' }}</div>
      </div>
      <div class="card"><div class="lbl">爬虫数</div><div class="big">{{ spiders.length }}</div>
        <div class="sub">project: {{ projectId.slice(0, 8) || '—' }}</div></div>
      <div class="card"><div class="lbl">实时事件 (WS)</div><div class="big">{{ events.length }}</div>
        <div class="sub">worker → Redis → WS</div></div>
    </div>

    <button class="btn" :disabled="busy || !projectId" @click="demoMainLink">
      {{ busy ? '执行中…' : '▶ 跑通主链路（建爬虫 → 触发 run）' }}
    </button>

    <div class="feed">
      <div class="feed-h">实时事件流 <span class="live">● LIVE</span></div>
      <div v-if="!events.length" class="empty">等待 worker 推送…（点上面按钮）</div>
      <pre v-for="(e, i) in events" :key="i" class="line">{{ e }}</pre>
    </div>
  </div>
</template>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 14px; }
h2 small { color: var(--muted); font-size: 13px; font-weight: 400; margin-left: 8px; }
.cards { display: flex; gap: 12px; }
.card { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.lbl { color: var(--muted); font-size: 12px; }
.big { font-size: 28px; font-weight: 700; }
.sub { color: var(--muted); font-size: 12px; }
.btn { align-self: flex-start; background: var(--accent); color: #fff; border: none; border-radius: 6px;
  padding: 9px 16px; font-weight: 600; cursor: pointer; }
.btn:disabled { opacity: .5; cursor: default; }
.feed { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.feed-h { font-weight: 600; margin-bottom: 8px; }
.live { color: var(--green); font-size: 12px; margin-left: 8px; }
.empty { color: var(--muted); font-size: 13px; }
.line { font-family: var(--mono); font-size: 12px; color: var(--green); margin: 2px 0; white-space: pre-wrap; }
</style>
