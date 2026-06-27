<script setup lang="ts">
// 巡检分诊（M4，默认首页）：三态计数 + 核心站盯梢 + 全量热力图 + 四层信号条 + 分诊队列(🟡闭环) + 实时流。
// 健康由真实四层信号驱动（M3 产出）；WS /ws/triage 推 run_done 实时刷新。
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, type TriageSummary, type HeatCell, type TriageItem } from '../api/client'
import { HEALTH_TO_DOT, HEALTH_LABEL, DOMAIN_LABEL, type HealthStatus, type DotState } from '../types'
import KpiCard from '../components/KpiCard.vue'
import Panel from '../components/Panel.vue'
import StatusDot from '../components/StatusDot.vue'
import Sparkline from '../components/Sparkline.vue'
import Pill from '../components/Pill.vue'
import { timeAgo } from '../utils/format'

const router = useRouter()
const summary = ref<TriageSummary | null>(null)
const cells = ref<HeatCell[]>([])
const coreSites = ref<TriageItem[]>([])
const queueItems = ref<TriageItem[]>([])
const qFilter = ref<'pending' | 'snoozed' | 'escalated'>('pending')
const events = ref<{ text: string; state: DotState }[]>([])
const wsLive = ref(false)
const loading = ref(true)
let ws: WebSocket | null = null
let poll: number | undefined

const dotOf = (h: string) => HEALTH_TO_DOT[h as HealthStatus] ?? 'unknown'
const QFILTERS = [
  { k: 'pending', l: '待处理' }, { k: 'snoozed', l: '已压制' }, { k: 'escalated', l: '已升级' },
] as const

const valueLabel = (it: TriageItem) =>
  `${it.priority}${it.is_core ? ' · 核心' : ''} · ${it.contribution_pct}%`

async function loadAll() {
  const [s, h, c] = await Promise.all([api.triageSummary(), api.triageHeatmap(), api.triageCoreSites(12)])
  summary.value = s; cells.value = h.cells; coreSites.value = c.sites
  await loadQueue()
  loading.value = false
}
async function loadQueue() {
  queueItems.value = (await api.triageQueue(qFilter.value)).items
}
function setFilter(f: typeof qFilter.value) { qFilter.value = f; loadQueue() }

async function confirmDry(it: TriageItem) {
  await api.triageSnooze(it.id, 3)
  await Promise.all([loadQueue(), api.triageSummary().then(s => (summary.value = s))])
}
async function escalate(it: TriageItem) {
  await api.triageEscalate(it.id)
  await loadQueue()
}

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/triage`)
  ws.onopen = () => (wsLive.value = true)
  ws.onclose = () => { wsLive.value = false; setTimeout(connectWs, 3000) }
  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data)
      const t = new Date(m.ts || Date.now()).toLocaleTimeString('zh-CN', { hour12: false })
      const newN = m.new ?? '—'
      events.value.unshift({
        text: `${t}  ${m.spider_name} · ${HEALTH_LABEL[m.verdict as HealthStatus] || m.verdict} · 新增 ${newN}`,
        state: dotOf(m.verdict),
      })
      if (events.value.length > 30) events.value.pop()
      loadAll() // run 改变了健康 → 刷新看板
    } catch { /* ignore */ }
  }
}

onMounted(() => {
  loadAll()
  connectWs()
  poll = window.setInterval(loadAll, 20000)
})
onUnmounted(() => { ws?.close(); clearInterval(poll) })

const fmtNum = (n: number | null | undefined) => (n === null || n === undefined ? '—' : n.toLocaleString())
</script>

<template>
  <div class="page">
    <div class="phead">
      <div>
        <h1>巡检分诊</h1>
        <div class="sub mono">2000 个爬虫，一眼看清谁挂了、谁没数据 · 健康由真实四层信号驱动</div>
      </div>
      <span class="grow" />
      <div class="live">
        <StatusDot :state="wsLive ? 'green' : 'unknown'" :live="wsLive" :size="7" />
        <span class="mono">{{ wsLive ? 'LIVE 实时流' : '重连中…' }}</span>
        <span v-if="summary?.last_inspection" class="mono ts">· 巡检 {{ timeAgo(summary.last_inspection) }}</span>
      </div>
    </div>

    <div v-if="loading" class="state mono">加载中…</div>
    <template v-else-if="summary">
      <!-- 三态计数 -->
      <div class="kpis">
        <KpiCard label="结构故障" :value="summary.counts.structural_fail" sub="🔴 改版挂了 · 需改配置" state="red" />
        <KpiCard label="数据干涸" :value="summary.counts.data_dry" sub="🟡 真没数据 · 待确认" state="yellow" />
        <KpiCard label="健康" :value="fmtNum(summary.counts.healthy)" sub="🟢 持续出数据" state="green" />
        <KpiCard label="本轮巡检" :value="fmtNum(summary.total)" sub="个受管爬虫" state="accent" />
      </div>

      <!-- 核心站盯梢 -->
      <Panel title="核心站盯梢" subtitle="~20 站贡献 80% 数据 · 干涸最致命">
        <div class="cores">
          <div v-for="s in coreSites" :key="s.id" class="core" :class="dotOf(s.health)" @click="router.push(`/spiders/${s.id}`)">
            <div class="core-h">
              <StatusDot :state="dotOf(s.health)" :live="dotOf(s.health) === 'green'" :size="7" />
              <span class="cname">{{ s.name }}</span>
            </div>
            <div class="core-n"><span class="today num">{{ fmtNum(s.today) }}</span><span class="base mono">/ 基线 {{ s.baseline }}</span></div>
            <Sparkline :values="s.spark" :state="dotOf(s.health)" :w="150" :h="28" />
          </div>
        </div>
      </Panel>

      <div class="cols">
        <!-- 左：热力图 + 四层信号条 -->
        <div class="lcol">
          <Panel title="全量健康热力图" :subtitle="`${cells.length} 站 · 红前黄中绿后`">
            <div class="heat">
              <span v-for="c in cells" :key="c.id" class="cell" :class="dotOf(c.health)"
                :title="`${c.name} · ${HEALTH_LABEL[c.health as HealthStatus]}`"
                @click="router.push(`/spiders/${c.id}`)" />
            </div>
            <div class="legend mono">
              <span><StatusDot state="red" :size="6" /> 结构故障</span>
              <span><StatusDot state="yellow" :size="6" /> 数据干涸</span>
              <span><StatusDot state="green" :size="6" /> 健康</span>
              <span><StatusDot state="unknown" :size="6" /> 未上报</span>
            </div>
          </Panel>

          <Panel title="四层信号模型" subtitle="区分『改版挂了』vs『真没数据』">
            <div class="sigflow">
              <div class="sig"><span class="sl mono">L1 HTTP</span><span class="sd">状态码 ≠200 → 挂了</span></div>
              <span class="arrow">→</span>
              <div class="sig"><span class="sl mono">L2 列表</span><span class="sd">命中 0 行 → 改版🔴</span></div>
              <span class="arrow">→</span>
              <div class="sig"><span class="sl mono">L3 详情</span><span class="sd">抽取率低 → 模板挂🔴</span></div>
              <span class="arrow">→</span>
              <div class="sig"><span class="sl mono">L4 数据</span><span class="sd">前三正常&新增0 → 真没数据🟡</span></div>
            </div>
          </Panel>

          <Panel title="实时事件流" subtitle="worker → Redis → WS">
            <div class="feed">
              <div v-if="!events.length" class="empty mono">等待 run 事件…（去详情点「运行一次」）</div>
              <div v-for="(e, i) in events" :key="i" class="ev mono">
                <StatusDot :state="e.state" :size="6" /><span class="evt">{{ e.text }}</span>
              </div>
            </div>
          </Panel>
        </div>

        <!-- 右：分诊队列 -->
        <Panel title="分诊队列" subtitle="价值 × 严重度排序">
          <template #actions>
            <div class="qfilters">
              <Pill v-for="f in QFILTERS" :key="f.k" :active="qFilter === f.k" @click="setFilter(f.k)">{{ f.l }}</Pill>
            </div>
          </template>
          <div v-if="!queueItems.length" class="empty mono">该筛选下无条目</div>
          <div v-for="it in queueItems" :key="it.id" class="qitem" :class="dotOf(it.health)">
            <div class="qmain" @click="router.push(`/spiders/${it.id}`)">
              <div class="qrow1">
                <StatusDot :state="dotOf(it.health)" :size="7" />
                <span class="qname">{{ it.name }}</span>
                <span class="qdomain mono">{{ DOMAIN_LABEL[(it.domain || 'other') as keyof typeof DOMAIN_LABEL] }}</span>
                <span class="grow" />
                <span class="qvalue mono">{{ valueLabel(it) }}</span>
              </div>
              <div class="qsig">{{ it.signal_text }}</div>
              <div class="qrow2">
                <Sparkline :values="it.spark" :state="dotOf(it.health)" :w="120" :h="24" />
                <span class="grow" />
                <span class="qnums mono">今日 {{ fmtNum(it.today) }} / 基线 {{ it.baseline }}</span>
              </div>
            </div>
            <div v-if="it.health === 'data_dry' && qFilter === 'pending'" class="qactions">
              <button class="qbtn ok" @click.stop="confirmDry(it)">✓ 确认真没数据</button>
              <button class="qbtn up" @click.stop="escalate(it)">↑ 升级故障</button>
            </div>
            <div v-else-if="it.snooze_until && qFilter === 'snoozed'" class="qsnooze mono">
              😴 压制至 {{ new Date(it.snooze_until).toLocaleDateString('zh-CN') }} · 出数据自动解除
            </div>
          </div>
          <div class="snote mono">🟡 闭环：确认真没数据 → 压制 N 天（出数据/到期自动解除）｜ 升级故障 → 提 P0 盯梢。</div>
        </Panel>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 14px; }
.phead { display: flex; align-items: flex-end; gap: 12px; }
.phead .grow { flex: 1; }
h1 { font-family: var(--font-head); font-weight: 600; font-size: 21px; margin: 0; color: var(--tx-1); }
.sub { font-size: 11.5px; color: var(--tx-muted); margin-top: 4px; }
.live { display: inline-flex; align-items: center; gap: 7px; font-size: 11px; color: var(--tx-4); }
.live .ts { color: var(--tx-weak); }
.state { padding: 48px; text-align: center; color: var(--tx-5); }

.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 13px; }

/* 核心站盯梢 */
.cores { display: flex; gap: 11px; overflow-x: auto; padding-bottom: 4px; }
.core { flex: none; width: 178px; background: var(--bg-inset); border: 1px solid var(--bd-card);
  border-top-width: 2px; border-radius: var(--r-card); padding: 11px 12px; cursor: pointer; transition: border-color .12s; }
.core:hover { border-color: var(--bd-accent); }
.core.red { border-top-color: var(--red-dot); }
.core.yellow { border-top-color: var(--yellow-dot); }
.core.green { border-top-color: var(--green-dot); }
.core.unknown { border-top-color: var(--unknown-dot); }
.core-h { display: flex; align-items: center; gap: 7px; margin-bottom: 8px; }
.cname { font-size: 12px; color: var(--tx-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.core-n { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; }
.today { font-size: 20px; font-weight: 600; color: var(--tx-1); }
.base { font-size: 10.5px; color: var(--tx-muted); }

.cols { display: grid; grid-template-columns: 1.1fr 1fr; gap: 14px; align-items: start; }
.lcol { display: flex; flex-direction: column; gap: 14px; }

/* 热力图 */
.heat { display: grid; grid-template-columns: repeat(auto-fill, 15px); gap: 4px; }
.cell { width: 15px; height: 15px; border-radius: 3px; cursor: pointer; transition: transform .1s; }
.cell:hover { transform: scale(1.35); }
.cell.red { background: var(--red-dot); box-shadow: 0 0 6px var(--red-dot); }
.cell.yellow { background: var(--yellow-dot); box-shadow: 0 0 5px var(--yellow-dot); }
.cell.green { background: var(--green-dot); opacity: .82; }
.cell.unknown { background: var(--unknown-dot); opacity: .5; }
.legend { display: flex; gap: 14px; margin-top: 12px; font-size: 10.5px; color: var(--tx-5); }
.legend span { display: inline-flex; align-items: center; gap: 5px; }

/* 四层信号条 */
.sigflow { display: flex; align-items: stretch; gap: 8px; flex-wrap: wrap; }
.sig { flex: 1; min-width: 120px; background: var(--bg-inset); border: 1px solid var(--bd-card); border-radius: var(--r-card); padding: 9px 11px; display: flex; flex-direction: column; gap: 4px; }
.sl { font-size: 11px; color: var(--accent); }
.sd { font-size: 10.5px; color: var(--tx-4); line-height: 1.4; }
.arrow { align-self: center; color: var(--tx-weak); }

/* 实时流 */
.feed { max-height: 150px; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; }
.ev { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--tx-3); }
.evt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.empty { color: var(--tx-5); font-size: 11.5px; padding: 6px 0; }

/* 分诊队列 */
.qfilters { display: flex; gap: 6px; }
.qitem { display: flex; align-items: stretch; gap: 0; border: 1px solid var(--bd-card); border-left-width: 3px; border-radius: var(--r-card); margin-bottom: 9px; overflow: hidden; }
.qitem.red { border-left-color: var(--red-dot); }
.qitem.yellow { border-left-color: var(--yellow-dot); }
.qitem.green { border-left-color: var(--green-dot); }
.qitem.unknown { border-left-color: var(--unknown-dot); }
.qmain { flex: 1; padding: 10px 12px; cursor: pointer; min-width: 0; }
.qmain:hover { background: var(--bg-inset); }
.qrow1 { display: flex; align-items: center; gap: 8px; }
.qrow1 .grow { flex: 1; }
.qname { font-size: 12.5px; color: var(--tx-1); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.qdomain { font-size: 10px; color: var(--tx-4); background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: 5px; padding: 1px 6px; }
.qvalue { font-size: 10.5px; color: var(--accent); white-space: nowrap; }
.qsig { font-size: 11px; color: var(--tx-4); margin: 6px 0 8px; line-height: 1.5; }
.qrow2 { display: flex; align-items: center; gap: 10px; }
.qrow2 .grow { flex: 1; }
.qnums { font-size: 10.5px; color: var(--tx-muted); white-space: nowrap; }
.qactions { display: flex; flex-direction: column; gap: 6px; padding: 10px; border-left: 1px solid var(--bd-divider); justify-content: center; }
.qbtn { font-family: var(--font-body); font-size: 10.5px; padding: 6px 9px; border-radius: 6px; cursor: pointer; white-space: nowrap; border: 1px solid var(--bd-control); background: var(--bg-chip); }
.qbtn.ok { color: var(--green-text); border-color: var(--green-bd); background: var(--green-bg); }
.qbtn.up { color: var(--red-text); border-color: var(--red-bd); background: var(--red-bg); }
.qsnooze { display: flex; align-items: center; padding: 10px 12px; font-size: 10.5px; color: var(--yellow-text); border-left: 1px solid var(--bd-divider); }
.snote { margin-top: 10px; font-size: 10.5px; color: var(--tx-weak); line-height: 1.5; }
</style>
