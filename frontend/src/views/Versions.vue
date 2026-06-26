<script setup lang="ts">
// 版本管理：左版本历史(线上绿辉光) + 右配置 diff(add绿/del红/ctx灰) + 回滚。
// 治理点：根除「复制文件当版本」——回滚=生成新版本。
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type DiffLine } from '../api/client'
import type { SpiderVersion } from '../types'
import Panel from '../components/Panel.vue'
import CtaButton from '../components/CtaButton.vue'
import StatusDot from '../components/StatusDot.vue'
import { timeAgo } from '../utils/format'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const versions = ref<SpiderVersion[]>([])
const sel = ref<number | null>(null)      // 选中（diff 的 to）
const base = ref<number | null>(null)     // 对比基准（diff 的 from）
const diff = ref<DiffLine[]>([])
const loading = ref(true)
const error = ref('')
const rolling = ref(false)

const live = computed(() => versions.value.find(v => v.is_live) ?? null)

async function loadVersions() {
  loading.value = true; error.value = ''
  try {
    versions.value = await api.listVersions(id.value)
    // 默认对比：线上版本 vs 其前一版
    const liveV = live.value?.version ?? versions.value[0]?.version ?? null
    sel.value = liveV
    base.value = versions.value.find(v => v.version < (liveV ?? 0))?.version ?? liveV
    await loadDiff()
  } catch (e) { error.value = String(e) } finally { loading.value = false }
}

async function loadDiff() {
  if (base.value == null || sel.value == null) { diff.value = []; return }
  if (base.value === sel.value) { diff.value = []; return }
  const lo = Math.min(base.value, sel.value)
  const hi = Math.max(base.value, sel.value)
  const res = await api.diffVersions(id.value, lo, hi)
  diff.value = res.lines
}

function pick(v: number) { sel.value = v; loadDiff() }
function pickBase(v: number) { base.value = v; loadDiff() }

async function rollback(v: number) {
  if (!confirm(`回滚到 v${v}？将生成一个新版本并置为线上（不复制文件）。`)) return
  rolling.value = true
  try { await api.rollback(id.value, v); await loadVersions() }
  finally { rolling.value = false }
}

const diffStat = computed(() => ({
  add: diff.value.filter(l => l.op === 'add').length,
  del: diff.value.filter(l => l.op === 'del').length,
}))

onMounted(loadVersions)
watch(id, loadVersions)
</script>

<template>
  <div class="page">
    <div class="crumb mono">
      <RouterLink to="/spiders" class="bk">爬虫</RouterLink> /
      <RouterLink :to="`/spiders/${id}`" class="bk">详情</RouterLink> / <span>版本</span>
    </div>

    <div class="phead">
      <h1>版本管理</h1>
      <span v-if="base != null && sel != null" class="cmp mono">对比 v{{ Math.min(base, sel) }} ↔ v{{ Math.max(base, sel) }}</span>
      <span class="grow" />
      <span class="stat mono"><b class="add">+{{ diffStat.add }}</b> <b class="del">-{{ diffStat.del }}</b></span>
    </div>

    <div class="warn mono">⚠ 配置即版本 · 回滚生成新版本 —— 根除「复制文件 / 注释当版本」（IC 项目 11 副本的教训）。</div>

    <div v-if="loading" class="state mono">加载中…</div>
    <div v-else-if="error" class="state err mono">加载失败：{{ error }}</div>
    <div v-else class="grid">
      <!-- 左版本历史 -->
      <Panel title="版本历史" :subtitle="`${versions.length} 个`">
        <ul class="vlist">
          <li v-for="v in versions" :key="v.id" class="vitem"
              :class="{ live: v.is_live, sel: v.version === sel }">
            <div class="vrow" @click="pick(v.version)">
              <span class="vno mono">v{{ v.version }}</span>
              <span v-if="v.is_live" class="livebadge mono"><StatusDot state="green" live :size="6" /> 线上</span>
              <span class="grow" />
              <span class="vts mono">{{ timeAgo(v.created_at) }}</span>
            </div>
            <div class="vmsg">{{ v.change_msg }}</div>
            <div class="vfoot mono">
              <span>by {{ v.author_name || '—' }}</span>
              <button class="basebtn" :class="{ on: v.version === base }" @click.stop="pickBase(v.version)">设为基准</button>
              <button v-if="!v.is_live" class="rb" :disabled="rolling" @click.stop="rollback(v.version)">↶ 回滚</button>
            </div>
          </li>
        </ul>
      </Panel>

      <!-- 右 diff -->
      <Panel title="配置 diff" :subtitle="base != null && sel != null ? `v${Math.min(base, sel)} → v${Math.max(base, sel)}` : ''">
        <template #actions>
          <CtaButton v-if="sel != null && live && sel !== live.version" variant="accent" :disabled="rolling"
            @click="rollback(sel)">↶ 回滚到 v{{ sel }}</CtaButton>
        </template>
        <div v-if="!diff.length" class="state mono">{{ base === sel ? '选择两个不同版本对比' : '两版本配置一致' }}</div>
        <pre v-else class="diff mono"><code v-for="(l, i) in diff" :key="i" class="dl" :class="l.op">{{ l.op === 'add' ? '+ ' : l.op === 'del' ? '- ' : '  ' }}{{ l.text }}</code></pre>
      </Panel>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 13px; }
.crumb { font-size: 11.5px; color: var(--tx-5); }
.bk { color: var(--accent); }
.phead { display: flex; align-items: baseline; gap: 12px; }
h1 { font-family: var(--font-head); font-weight: 600; font-size: 21px; margin: 0; color: var(--tx-1); }
.cmp { font-size: 12px; color: var(--tx-4); }
.grow { flex: 1; }
.stat { font-size: 12px; }
.stat .add { color: var(--green-text); margin-right: 8px; }
.stat .del { color: var(--red-text); }
.warn { font-size: 11px; color: var(--yellow-text); background: var(--yellow-bg); border: 1px solid var(--yellow-bd); border-radius: var(--r-card); padding: 9px 13px; }

.grid { display: grid; grid-template-columns: 320px 1fr; gap: 14px; align-items: start; }
.state { padding: 36px; text-align: center; color: var(--tx-5); font-size: 12.5px; }
.state.err { color: var(--red-text); }

.vlist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.vitem { border: 1px solid var(--bd-card); border-radius: var(--r-card); padding: 10px 12px; cursor: pointer; transition: border-color .12s, background .12s; }
.vitem:hover { border-color: var(--bd-accent); }
.vitem.sel { border-color: var(--accent); background: var(--accent-select-bg); }
.vitem.live { box-shadow: inset 2px 0 0 var(--green-dot); }
.vrow { display: flex; align-items: center; gap: 8px; }
.vno { font-size: 13px; font-weight: 600; color: var(--tx-1); }
.livebadge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; color: var(--green-text); background: var(--green-bg); border: 1px solid var(--green-bd); border-radius: 5px; padding: 1px 6px; }
.vts { font-size: 10.5px; color: var(--tx-weak); }
.vmsg { font-size: 12px; color: var(--tx-3); margin: 7px 0 8px; line-height: 1.5; }
.vfoot { display: flex; align-items: center; gap: 10px; font-size: 10.5px; color: var(--tx-muted); }
.vfoot > span { flex: 1; }
.basebtn, .rb { background: none; border: 1px solid var(--bd-control); border-radius: 5px; padding: 2px 7px; font-size: 10px; cursor: pointer; color: var(--tx-4); font-family: var(--font-mono); }
.basebtn.on { border-color: var(--accent); color: var(--accent); }
.rb { color: var(--tx-3); }
.rb:hover { border-color: var(--accent); color: var(--accent); }

.diff { margin: 0; background: var(--bg-terminal); border-radius: var(--r-card); padding: 12px 14px; overflow: auto; max-height: 540px; }
.dl { display: block; font-size: 11.5px; line-height: 1.7; white-space: pre; color: var(--tx-4); }
.dl.add { color: var(--green-text); background: #0f1a1420; }
.dl.del { color: var(--red-text); background: #1a111020; }
.dl.ctx { color: var(--tx-5); }
</style>
