<script setup lang="ts">
// 爬虫列表：左筛选栏 + 主表。关键叙事「成功率高 ≠ 健康」。行点击进详情。
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { api, asItems } from '../api/client'
import { useSession } from '../stores/session'
import type { Spider, HealthStatus, ExecStatus } from '../types'
import { HEALTH_LABEL, EXEC_LABEL } from '../types'
import HealthBadge from '../components/HealthBadge.vue'
import ExecBadge from '../components/ExecBadge.vue'
import StatusDot from '../components/StatusDot.vue'
import CtaButton from '../components/CtaButton.vue'
import { timeAgo, pct, domainLabel } from '../utils/format'

const router = useRouter()
const session = useSession()
const { currentId } = storeToRefs(session)

const rows = ref<Spider[]>([])
const loading = ref(true)
const error = ref('')

// 筛选态（多选，客户端过滤；demo 规模够用且即时）
const fHealth = ref<Set<HealthStatus>>(new Set())
const fExec = ref<Set<ExecStatus>>(new Set())
const fOwner = ref<Set<string>>(new Set())
const q = ref('')

const HEALTHS: HealthStatus[] = ['structural_fail', 'data_dry', 'healthy', 'unknown']
const EXECS: ExecStatus[] = ['running', 'paused', 'failed', 'disabled']
const owners = computed(() => [...new Set(rows.value.map(r => r.owner_name).filter(Boolean))] as string[])

function toggle(kind: 'health' | 'exec' | 'owner', v: string) {
  const r = kind === 'health' ? fHealth : kind === 'exec' ? fExec : fOwner
  const s = new Set<string>(r.value as Set<string>)
  s.has(v) ? s.delete(v) : s.add(v)
  ;(r.value as Set<string>) = s
}

const filtered = computed(() => rows.value.filter(r => {
  if (fHealth.value.size && !fHealth.value.has(r.health_status)) return false
  if (fExec.value.size && !fExec.value.has(r.status)) return false
  if (fOwner.value.size && !(r.owner_name && fOwner.value.has(r.owner_name))) return false
  if (q.value && !r.name.toLowerCase().includes(q.value.toLowerCase())) return false
  return true
}))

// 叙事命中：执行成功率高(>=95%) 但健康非 🟢
const hasParadox = computed(() =>
  filtered.value.some(r => (r.success_rate ?? 0) >= 0.95 && r.health_status !== 'healthy'),
)

async function load() {
  if (!currentId.value) return
  loading.value = true
  error.value = ''
  try {
    rows.value = asItems(await api.listSpiders(currentId.value, { page_size: 200 }))
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

const newHint = ref(false)

onMounted(async () => {
  await session.load()
  await load()
})
watch(currentId, load)

function clearFilters() {
  fHealth.value = new Set(); fExec.value = new Set(); fOwner.value = new Set(); q.value = ''
}
const filterCount = computed(() => fHealth.value.size + fExec.value.size + fOwner.value.size + (q.value ? 1 : 0))
</script>

<template>
  <div class="page">
    <div class="phead">
      <div>
        <h1>爬虫</h1>
        <div class="sub mono">{{ session.current?.name }} · {{ filtered.length }} / {{ rows.length }} 个</div>
      </div>
      <span class="grow" />
      <CtaButton variant="accent" @click="newHint = true">+ 新建爬虫</CtaButton>
    </div>

    <div class="layout">
      <!-- 左筛选栏 -->
      <aside class="filters">
        <div class="fhead">
          <span class="mono">筛选</span>
          <button v-if="filterCount" class="clear mono" @click="clearFilters">清除 {{ filterCount }}</button>
        </div>

        <div class="fgroup">
          <div class="ftitle mono">搜索</div>
          <input v-model="q" class="search mono" placeholder="名称…" />
        </div>

        <div class="fgroup">
          <div class="ftitle mono">健康态</div>
          <label v-for="h in HEALTHS" :key="h" class="check">
            <input type="checkbox" :checked="fHealth.has(h)" @change="toggle('health', h)" />
            <StatusDot :state="h === 'structural_fail' ? 'red' : h === 'data_dry' ? 'yellow' : h === 'healthy' ? 'green' : 'unknown'" :size="7" />
            <span>{{ HEALTH_LABEL[h] }}</span>
          </label>
        </div>

        <div class="fgroup">
          <div class="ftitle mono">执行态</div>
          <label v-for="e in EXECS" :key="e" class="check">
            <input type="checkbox" :checked="fExec.has(e)" @change="toggle('exec', e)" />
            <span>{{ EXEC_LABEL[e] }}</span>
          </label>
        </div>

        <div class="fgroup" v-if="owners.length">
          <div class="ftitle mono">负责人</div>
          <label v-for="o in owners" :key="o" class="check">
            <input type="checkbox" :checked="fOwner.has(o)" @change="toggle('owner', o)" />
            <span>{{ o }}</span>
          </label>
        </div>
      </aside>

      <!-- 主表 -->
      <div class="main">
        <div class="tablewrap">
          <table class="tbl">
            <thead>
              <tr>
                <th>名称</th><th>域</th><th>负责人</th>
                <th>执行态</th><th>健康</th>
                <th>调度</th><th>上次</th><th class="r">成功率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="8" class="state">加载中…</td></tr>
              <tr v-else-if="error"><td colspan="8" class="state err">加载失败：{{ error }}</td></tr>
              <tr v-else-if="!filtered.length"><td colspan="8" class="state">无匹配爬虫</td></tr>
              <tr v-for="r in filtered" :key="r.id" class="row" @click="router.push(`/spiders/${r.id}`)">
                <td class="name">
                  <span v-if="r.is_core" class="core" title="核心站">★</span>
                  {{ r.name }}
                </td>
                <td><span class="domain mono">{{ domainLabel(r.domain) }}</span></td>
                <td class="owner">{{ r.owner_name || '—' }}</td>
                <td><ExecBadge :status="r.status" /></td>
                <td><HealthBadge :status="r.health_status" /></td>
                <td><span class="cron mono">{{ r.cron || '—' }}</span></td>
                <td class="last mono">{{ timeAgo(r.last_run_at) }}</td>
                <td class="r sr mono" :class="{ paradox: (r.success_rate ?? 0) >= 0.95 && r.health_status !== 'healthy' }">
                  {{ pct(r.success_rate) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasParadox" class="paradox-bar mono">
          ⚠ 跑成功率 ≠ 出数据 —— 执行成功率高 <b>不等于</b> 健康。看健康灯（🔴 改版 / 🟡 没数据），别只看成功率。
        </div>
      </div>
    </div>

    <!-- 新建提示（向导 M2） -->
    <div v-if="newHint" class="hint" @click.self="newHint = false">
      <div class="hint-box">
        <div class="ht">新建爬虫向导</div>
        <p class="hd">含「新建查重」防冒充的 7 步向导规划于 <b class="mono">M2</b>。M1 先打通列表 → 详情 → 版本主线。</p>
        <CtaButton variant="ghost" @click="newHint = false">知道了</CtaButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.phead { display: flex; align-items: flex-end; gap: 12px; }
.phead .grow { flex: 1; }
h1 { font-family: var(--font-head); font-weight: 600; font-size: 21px; margin: 0; color: var(--tx-1); }
.sub { font-size: 11.5px; color: var(--tx-muted); margin-top: 4px; }

.layout { display: grid; grid-template-columns: 188px 1fr; gap: 16px; align-items: start; }

/* 筛选栏 */
.filters {
  background: var(--bg-panel); border: 1px solid var(--bd-panel); border-radius: var(--r-panel);
  padding: 13px; display: flex; flex-direction: column; gap: 16px; position: sticky; top: 70px;
}
.fhead { display: flex; align-items: center; }
.fhead .mono { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: var(--tx-weak); }
.clear { margin-left: auto; background: none; border: none; color: var(--accent); cursor: pointer; font-size: 10.5px; }
.fgroup { display: flex; flex-direction: column; gap: 7px; }
.ftitle { font-size: 10.5px; color: var(--tx-muted); letter-spacing: .5px; }
.search { background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 7px 9px; color: var(--tx-1); font-size: 12px; outline: none; }
.search:focus { border-color: var(--accent); }
.check { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--tx-3); cursor: pointer; }
.check:hover { color: var(--tx-1); }
.check input { accent-color: var(--accent); }

/* 表 */
.tablewrap { background: var(--bg-panel); border: 1px solid var(--bd-panel); border-radius: var(--r-panel); overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; }
thead th {
  text-align: left; font-family: var(--font-mono); font-weight: 500; font-size: 10.5px;
  letter-spacing: .5px; text-transform: uppercase; color: var(--tx-muted);
  padding: 11px 14px; border-bottom: 1px solid var(--bd-divider); white-space: nowrap;
}
th.r, td.r { text-align: right; }
tbody td { padding: 12px 14px; border-bottom: 1px solid var(--bd-row); font-size: 13px; color: var(--tx-2); vertical-align: middle; }
tbody tr:last-child td { border-bottom: none; }
.row { cursor: pointer; transition: background .1s; }
.row:hover td { background: var(--bg-inset); }
.name { font-weight: 500; color: var(--tx-1); white-space: nowrap; }
.core { color: var(--accent); margin-right: 5px; font-size: 11px; }
.domain { font-size: 11px; color: var(--tx-4); background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: 5px; padding: 2px 7px; }
.owner { color: var(--tx-3); white-space: nowrap; }
.cron { font-size: 11.5px; color: var(--tx-4); }
.last { font-size: 11.5px; color: var(--tx-5); white-space: nowrap; }
.sr { color: var(--tx-2); }
.sr.paradox { color: var(--red-text); }

.paradox-bar {
  margin-top: 12px; font-size: 11.5px; color: var(--yellow-text);
  background: var(--yellow-bg); border: 1px solid var(--yellow-bd); border-radius: var(--r-card);
  padding: 10px 14px; line-height: 1.6;
}
.paradox-bar b { color: var(--yellow-dot); }

/* 新建提示 */
.hint { position: fixed; inset: 0; background: #0007; display: grid; place-items: center; z-index: 50; }
.hint-box { background: var(--bg-panel); border: 1px solid var(--bd-card); border-radius: var(--r-panel); padding: 22px; max-width: 360px; text-align: center; }
.ht { font-family: var(--font-head); font-weight: 600; font-size: 16px; color: var(--tx-1); margin-bottom: 8px; }
.hd { font-size: 12.5px; color: var(--tx-4); line-height: 1.7; margin: 0 0 16px; }
.state { text-align: center; color: var(--tx-5); padding: 36px; font-size: 13px; }
.state.err { color: var(--red-text); }
</style>
