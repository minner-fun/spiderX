<script setup lang="ts">
// 爬虫详情：头部卡 + 分层健康信号表 + 数据基线柱图 + 右栏(元信息/最近运行/验证修复)。
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type { Spider, Run } from '../types'
import { HEALTH_LABEL, EXEC_LABEL } from '../types'
import HealthBadge from '../components/HealthBadge.vue'
import ExecBadge from '../components/ExecBadge.vue'
import StatusDot from '../components/StatusDot.vue'
import CtaButton from '../components/CtaButton.vue'
import Panel from '../components/Panel.vue'
import BaselineBars from '../components/BaselineBars.vue'
import { signalLayers, conclusion } from '../utils/health'
import { timeAgo, pct, domainLabel } from '../utils/format'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const spider = ref<Spider | null>(null)
const runs = ref<Run[]>([])
const loading = ref(true)
const error = ref('')
const running = ref(false)

const layers = computed(() => signalLayers(spider.value?.signals))
const concl = computed(() => conclusion(spider.value?.health_status ?? 'unknown'))

// 基线柱图：runs 按时间正序，取 dedup_new（null→0）
const chrono = computed(() => [...runs.value].reverse())
const chartLabels = computed(() => chrono.value.map(r => new Date(r.created_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })))
const chartValues = computed(() => chrono.value.map(r => r.signals?.dedup_new ?? 0))
const cliff = computed(() => (spider.value?.health_status ?? 'healthy') !== 'healthy')

const latestRun = computed(() => runs.value[0] ?? null)
// 陷阱：跑成功但新增 0
const trap = computed(() =>
  latestRun.value?.exec_status === 'success' && (latestRun.value?.signals?.dedup_new ?? 0) === 0,
)

async function load() {
  loading.value = true; error.value = ''
  try {
    const [s, r] = await Promise.all([api.getSpider(id.value), api.listRuns(id.value, 10)])
    spider.value = s; runs.value = r
  } catch (e) { error.value = String(e) } finally { loading.value = false }
}
async function runOnce() {
  // 真实执行经 worker 异步完成（抓取~1-2s），轮询刷新看健康/信号更新
  running.value = true
  try {
    await api.runSpider(id.value)
    for (const d of [1200, 2600]) setTimeout(load, d)
  } finally {
    setTimeout(() => (running.value = false), 2800)
  }
}

onMounted(load)
watch(id, load)
</script>

<template>
  <div v-if="loading" class="state mono">加载中…</div>
  <div v-else-if="error" class="state err mono">加载失败：{{ error }}</div>
  <div v-else-if="spider" class="page">
    <!-- 面包屑 -->
    <div class="crumb mono">
      <RouterLink to="/spiders" class="bk">爬虫</RouterLink> / <span>{{ spider.name }}</span>
    </div>

    <!-- 头部卡 -->
    <div class="head">
      <div class="hleft">
        <div class="title">
          <span v-if="spider.is_core" class="core" title="核心站">★</span>
          {{ spider.name }}
        </div>
        <div class="meta mono">
          <span class="domain">{{ domainLabel(spider.domain) }}</span>
          <span>负责人 {{ spider.owner_name || '—' }}</span>
          <span>线上 v{{ spider.current_version ?? '—' }}</span>
          <span>{{ spider.cron || '无调度' }}</span>
        </div>
      </div>
      <div class="hbadges">
        <HealthBadge :status="spider.health_status" />
        <ExecBadge :status="spider.status" />
      </div>
      <div class="hactions">
        <CtaButton variant="accent" @click="router.push(`/spiders/${id}/rules`)">验证修复</CtaButton>
        <CtaButton variant="ghost" @click="router.push(`/spiders/${id}/rules`)">编辑规则</CtaButton>
        <CtaButton variant="ghost" :disabled="running" @click="runOnce">{{ running ? '运行中…' : '运行一次' }}</CtaButton>
      </div>
    </div>

    <div class="grid">
      <!-- 左主列 -->
      <div class="col">
        <Panel title="分层健康信号" subtitle="区分『改版挂了』vs『真没数据』">
          <table class="sig">
            <thead><tr><th>层</th><th>信号</th><th>当前值</th><th>判定</th></tr></thead>
            <tbody>
              <tr v-for="l in layers" :key="l.layer">
                <td class="ly mono">{{ l.layer }}</td>
                <td class="sn">{{ l.name }}</td>
                <td class="sv mono" :class="l.verdict">{{ l.value }}</td>
                <td class="vd">
                  <span class="vbadge" :style="{ color: `var(--${l.verdict}-text)`, background: `var(--${l.verdict}-bg)`, borderColor: `var(--${l.verdict}-bd)` }">
                    <StatusDot :state="l.verdict" :size="6" /> {{ l.note }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="concl" :style="{ color: `var(--${concl.state}-text)`, background: `var(--${concl.state}-bg)`, borderColor: `var(--${concl.state}-bd)` }">
            <b>结论</b> · {{ concl.text }}
          </div>
          <div class="legend mono">
            <span><StatusDot state="green" :size="6" /> 正常</span>
            <span><StatusDot state="red" :size="6" /> 结构故障</span>
            <span><StatusDot state="yellow" :size="6" /> 数据干涸</span>
            <span><StatusDot state="unknown" :size="6" /> 未上报（代码驱动未按契约回报该层）</span>
          </div>
        </Panel>

        <Panel title="数据量基线趋势" subtitle="去重后新增 · 末柱断崖=异常">
          <BaselineBars :labels="chartLabels" :values="chartValues" :cliff="cliff" />
        </Panel>
      </div>

      <!-- 右栏 -->
      <div class="col">
        <Panel title="元信息">
          <div class="kv">
            <div class="k">业务价值</div>
            <div class="v"><span class="prio">{{ spider.priority }}</span> 手填 · 贡献 {{ spider.contribution_pct }}%{{ spider.is_core ? ' · 核心站' : '' }}</div>
            <div class="k">负责人</div><div class="v">{{ spider.owner_name || '—' }}</div>
            <div class="k">标签</div>
            <div class="v tags"><span v-for="t in spider.tags" :key="t" class="tag mono">{{ t }}</span></div>
            <div class="k">线上版本</div>
            <div class="v"><RouterLink :to="`/spiders/${id}/versions`" class="vlink mono">v{{ spider.current_version ?? '—' }} →</RouterLink></div>
            <div class="k">成功率</div>
            <div class="v mono" :class="{ paradox: (spider.success_rate ?? 0) >= 0.95 && spider.health_status !== 'healthy' }">{{ pct(spider.success_rate) }}</div>
          </div>
        </Panel>

        <Panel title="最近运行">
          <div v-if="trap" class="trap mono">⚠ 上次跑成功但去重后新增 = 0 —— 执行成功 ≠ 出数据</div>
          <div v-if="!runs.length" class="empty mono">暂无运行记录</div>
          <ul class="runs">
            <li v-for="r in runs.slice(0, 6)" :key="r.id" class="run">
              <StatusDot :state="r.exec_status === 'success' ? 'green' : r.exec_status === 'failed' ? 'red' : 'unknown'" :size="6" />
              <span class="rmono mono">{{ r.exec_status }}</span>
              <span class="rsep">·</span>
              <span class="rnew mono">新增 {{ r.signals?.dedup_new ?? '—' }}</span>
              <span class="grow" />
              <span class="rts mono">{{ timeAgo(r.created_at) }}</span>
            </li>
          </ul>
        </Panel>

        <Panel title="验证修复">
          <p class="fix">健康判定基于最近 Run 的四层信号。<b :style="{ color: `var(--${concl.state}-text)` }">{{ HEALTH_LABEL[spider.health_status] }}</b> · {{ EXEC_LABEL[spider.status] }}。</p>
          <CtaButton variant="accent" @click="router.push(`/spiders/${id}/rules`)">前往规则编辑器修复 →</CtaButton>
        </Panel>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 14px; }
.state { padding: 48px; text-align: center; color: var(--tx-5); }
.state.err { color: var(--red-text); }
.crumb { font-size: 11.5px; color: var(--tx-5); }
.bk { color: var(--accent); }

.head {
  display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 16px;
  background: var(--bg-panel); border: 1px solid var(--bd-panel); border-radius: var(--r-panel); padding: 16px 18px;
}
.title { font-family: var(--font-head); font-weight: 600; font-size: 19px; color: var(--tx-1); }
.core { color: var(--accent); margin-right: 6px; }
.meta { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; font-size: 11.5px; color: var(--tx-5); }
.meta .domain { color: var(--tx-4); }
.hbadges { display: flex; gap: 8px; }
.hactions { display: flex; gap: 8px; }

.grid { display: grid; grid-template-columns: 1fr 320px; gap: 14px; align-items: start; }
.col { display: flex; flex-direction: column; gap: 14px; }

/* 信号表 */
.sig { width: 100%; border-collapse: collapse; }
.sig th { text-align: left; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: var(--tx-muted); padding: 0 10px 9px; }
.sig td { padding: 9px 10px; border-top: 1px solid var(--bd-row); font-size: 12.5px; }
.ly { color: var(--tx-3); white-space: nowrap; }
.sn { color: var(--tx-4); }
.sv { font-weight: 600; }
.sv.green { color: var(--green-text); } .sv.red { color: var(--red-text); } .sv.yellow { color: var(--yellow-text); } .sv.unknown { color: var(--tx-5); }
.vbadge { display: inline-flex; align-items: center; gap: 6px; padding: 3px 8px; border: 1px solid; border-radius: var(--r-badge); font-size: 11px; white-space: nowrap; }
.concl { margin-top: 13px; padding: 10px 13px; border: 1px solid; border-radius: var(--r-card); font-size: 12px; line-height: 1.6; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px; font-size: 10.5px; color: var(--tx-5); }
.legend span { display: inline-flex; align-items: center; gap: 5px; }

/* 右栏 */
.kv { display: grid; grid-template-columns: 72px 1fr; gap: 11px 12px; align-items: baseline; }
.k { font-size: 11px; color: var(--tx-muted); }
.v { font-size: 12.5px; color: var(--tx-2); }
.v.paradox { color: var(--red-text); }
.prio { color: var(--accent); font-weight: 600; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag { font-size: 10.5px; color: var(--tx-4); background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: 5px; padding: 2px 7px; }
.vlink { color: var(--accent); }
.trap { font-size: 11px; color: var(--yellow-text); background: var(--yellow-bg); border: 1px solid var(--yellow-bd); border-radius: var(--r-card); padding: 8px 11px; margin-bottom: 11px; line-height: 1.5; }
.empty { color: var(--tx-5); font-size: 12px; }
.runs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.run { display: flex; align-items: center; gap: 7px; padding: 8px 0; border-top: 1px solid var(--bd-row); font-size: 11.5px; }
.run:first-child { border-top: none; }
.rmono { color: var(--tx-3); } .rsep { color: var(--tx-weak); } .rnew { color: var(--tx-4); }
.grow { flex: 1; } .rts { color: var(--tx-weak); }
.fix { font-size: 12px; color: var(--tx-4); line-height: 1.7; margin: 0 0 13px; }
</style>
