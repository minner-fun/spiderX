<script setup lang="ts">
// 调度 · 对账（M3）：对账 KPI + 队列水位 + 24h 调度时间线(gantt) + 死信。
// 纲要 §10：Run 记录作真相源，对账扫「已分发但从未完成」防静默丢数据。
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, type ScheduleOverview } from '../api/client'
import { domainLabel } from '../utils/format'
import KpiCard from '../components/KpiCard.vue'
import Panel from '../components/Panel.vue'
import StatusDot from '../components/StatusDot.vue'
import type { DotState } from '../types'

const router = useRouter()
const data = ref<ScheduleOverview | null>(null)
const loading = ref(true)
const error = ref('')
let timer: number | undefined

const DOMAIN_DOT: Record<string, DotState> = { bid: 'cyan', ic: 'yellow' }
const HOURS = [0, 4, 8, 12, 16, 20, 24]

const enabledSchedules = computed(() => data.value?.schedules.filter(s => s.enabled) ?? [])
const maxDepth = computed(() => Math.max(1, ...(data.value?.queues.map(q => q.depth) ?? [1])))

async function load() {
  try {
    data.value = await api.scheduleOverview()
    error.value = ''
  } catch (e) { error.value = String(e) } finally { loading.value = false }
}

function fmtTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

onMounted(() => { load(); timer = window.setInterval(load, 15000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="page">
    <div class="phead">
      <h1>调度 · 对账</h1>
      <span class="sub mono">Beat cron + 抖动 · Run 记录作真相源 · 每 15s 刷新</span>
    </div>

    <div v-if="loading" class="state mono">加载中…</div>
    <div v-else-if="error" class="state err mono">加载失败：{{ error }}</div>
    <template v-else-if="data">
      <!-- 对账 KPI -->
      <div class="kpis">
        <KpiCard label="已分发 24h" :value="data.reconcile.dispatched" sub="dispatched" state="accent" />
        <KpiCard label="进行中" :value="data.reconcile.started" sub="running / queued" state="green" />
        <KpiCard label="已完成 24h" :value="data.reconcile.completed" sub="finished" state="green" />
        <KpiCard label="已分发未完成" :value="data.reconcile.stuck" sub="stuck · 对账可见" :state="data.reconcile.stuck ? 'red' : 'unknown'" />
        <KpiCard label="DLQ 死信" :value="data.reconcile.dlq" sub="dead-letter" :state="data.reconcile.dlq ? 'red' : 'unknown'" />
      </div>

      <div class="cols">
        <!-- 调度时间线 -->
        <Panel title="调度时间线" subtitle="未来 24h · 域着色">
          <div class="gantt">
            <div class="axis">
              <span class="alabel mono" />
              <div class="track ruler">
                <span v-for="h in HOURS" :key="h" class="tick mono" :style="{ left: (h / 24 * 100) + '%' }">+{{ h }}h</span>
              </div>
            </div>
            <div v-for="s in enabledSchedules" :key="s.spider_id" class="grow-row" @click="router.push(`/spiders/${s.spider_id}`)">
              <span class="alabel">
                <StatusDot :state="DOMAIN_DOT[s.domain] || 'unknown'" :size="6" />
                <span class="sname">{{ s.spider_name }}</span>
                <span class="cron mono">{{ s.cron }}</span>
              </span>
              <div class="track">
                <span v-for="(f, i) in s.fires" :key="i" class="fire"
                  :class="s.domain"
                  :style="{ left: (f / 24 * 100) + '%' }" :title="`+${f}h`" />
              </div>
            </div>
            <div v-if="!enabledSchedules.length" class="empty mono">无启用调度</div>
          </div>
        </Panel>

        <!-- 队列水位 -->
        <Panel title="队列水位" subtitle="default / high / retry / low">
          <div class="queues">
            <div v-for="q in data.queues" :key="q.name" class="qrow">
              <span class="qname mono">{{ q.name }}</span>
              <div class="qbar"><div class="qfill" :style="{ width: (q.depth / maxDepth * 100) + '%' }" /></div>
              <span class="qdepth mono">{{ q.depth }}</span>
            </div>
          </div>
          <div class="note mono">M3 统一默认队列；命名队列 default/high/retry/low 后续接入。</div>
        </Panel>
      </div>

      <!-- 对账说明 -->
      <div class="recon-bar mono" :class="{ alert: data.reconcile.stuck || data.reconcile.dlq }">
        <template v-if="data.reconcile.stuck || data.reconcile.dlq">
          ⚠ 对账发现 <b>{{ data.reconcile.stuck }}</b> 个「已分发但从未完成」+ <b>{{ data.reconcile.dlq }}</b> 个死信 —— late-ack + Run 记录使其<b>不可能静默消失</b>，对账器每 2 分钟扫描标记。
        </template>
        <template v-else>
          ✓ 无 stuck / DLQ —— late-ack（执行成功才 ack）+ Run 记录作唯一真相源 + 对账器兜底，杜绝 IC 项目那种「确认进队列然后没了」。
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 14px; }
.phead { display: flex; align-items: baseline; gap: 12px; }
h1 { font-family: var(--font-head); font-weight: 600; font-size: 21px; margin: 0; color: var(--tx-1); }
.sub { font-size: 11.5px; color: var(--tx-muted); }
.state { padding: 44px; text-align: center; color: var(--tx-5); }
.state.err { color: var(--red-text); }

.kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.cols { display: grid; grid-template-columns: 1.7fr 1fr; gap: 14px; align-items: start; }

/* gantt */
.gantt { display: flex; flex-direction: column; gap: 3px; }
.axis { margin-bottom: 6px; }
.grow-row, .axis { display: grid; grid-template-columns: 200px 1fr; align-items: center; gap: 10px; }
.grow-row { padding: 5px 0; cursor: pointer; border-radius: 6px; }
.grow-row:hover { background: var(--bg-inset); }
.alabel { display: flex; align-items: center; gap: 7px; min-width: 0; }
.sname { font-size: 12px; color: var(--tx-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.cron { font-size: 9.5px; color: var(--tx-weak); white-space: nowrap; }
.track { position: relative; height: 16px; background: var(--bg-inset); border: 1px solid var(--bd-divider); border-radius: 5px; }
.track.ruler { background: none; border: none; height: 14px; }
.tick { position: absolute; top: 0; font-size: 9px; color: var(--tx-weak); transform: translateX(-50%); }
.fire { position: absolute; top: 50%; width: 6px; height: 6px; border-radius: 50%; transform: translate(-50%, -50%); }
.fire.bid { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
.fire.ic { background: var(--yellow-dot); box-shadow: 0 0 6px var(--yellow-dot); }
.empty { color: var(--tx-5); font-size: 12px; padding: 10px 0; }

/* 队列 */
.queues { display: flex; flex-direction: column; gap: 11px; }
.qrow { display: grid; grid-template-columns: 56px 1fr 36px; align-items: center; gap: 10px; }
.qname { font-size: 11.5px; color: var(--tx-3); }
.qbar { height: 10px; background: var(--bg-inset); border: 1px solid var(--bd-divider); border-radius: 5px; overflow: hidden; }
.qfill { height: 100%; background: var(--accent-grad); box-shadow: 0 0 8px #4cc9e055; min-width: 0; transition: width .3s; }
.qdepth { font-size: 11.5px; color: var(--tx-3); text-align: right; }
.note { margin-top: 12px; font-size: 10.5px; color: var(--tx-weak); line-height: 1.5; }

.recon-bar { font-size: 11.5px; padding: 11px 14px; border-radius: var(--r-card); line-height: 1.6;
  color: var(--green-text); background: var(--green-bg); border: 1px solid var(--green-bd); }
.recon-bar.alert { color: var(--red-text); background: var(--red-bg); border-color: var(--red-bd); }
.recon-bar b { font-weight: 600; }
</style>
