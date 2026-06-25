<script setup lang="ts">
// 原子组件像素校验页（M1 第 1 步）。仅 dev 自检用，不进导航。
import StatusDot from '../components/StatusDot.vue'
import HealthBadge from '../components/HealthBadge.vue'
import ExecBadge from '../components/ExecBadge.vue'
import Panel from '../components/Panel.vue'
import KpiCard from '../components/KpiCard.vue'
import Pill from '../components/Pill.vue'
import CtaButton from '../components/CtaButton.vue'
import { ref } from 'vue'
import type { HealthStatus, ExecStatus } from '../types'

const healths: HealthStatus[] = ['structural_fail', 'data_dry', 'healthy', 'unknown']
const execs: ExecStatus[] = ['running', 'paused', 'failed', 'disabled']
const filter = ref('all')
const filters = [
  { k: 'all', l: '全部' }, { k: 'pending', l: '待处理' },
  { k: 'snoozed', l: '已压制' }, { k: 'confirmed', l: '已确认' },
]
</script>

<template>
  <div class="sg hf-grid">
    <h1>SpiderX 原子组件 · Styleguide</h1>
    <p class="lead">深色控制台「Mission Control」· 唯一令牌源 tokens.css。健康三态色严格守恒，磷光青只用于交互/品牌。</p>

    <Panel title="StatusDot 状态灯" subtitle="8px + 辉光 · live 呼吸">
      <div class="row">
        <span class="cell"><StatusDot state="red" /> red</span>
        <span class="cell"><StatusDot state="yellow" /> yellow</span>
        <span class="cell"><StatusDot state="green" /> green</span>
        <span class="cell"><StatusDot state="unknown" /> unknown</span>
        <span class="cell"><StatusDot state="cyan" /> cyan</span>
        <span class="cell"><StatusDot state="green" live /> live 脉冲</span>
      </div>
    </Panel>

    <Panel title="HealthBadge 健康三态" subtitle="数据语义">
      <div class="row"><HealthBadge v-for="h in healths" :key="h" :status="h" /></div>
    </Panel>

    <Panel title="ExecBadge 执行态" subtitle="与健康态分离">
      <div class="row"><ExecBadge v-for="e in execs" :key="e" :status="e" /></div>
    </Panel>

    <Panel title="KpiCard 指标卡">
      <div class="kpis">
        <KpiCard label="结构故障" :value="23" sub="🔴 需改配置" state="red" />
        <KpiCard label="数据干涸" :value="41" sub="🟡 待人工确认" state="yellow" />
        <KpiCard label="健康" value="1,936" sub="🟢 正常出数据" state="green" />
        <KpiCard label="本轮巡检" value="2,000" sub="12:00 · 每小时" state="accent" />
      </div>
    </Panel>

    <Panel title="Pill 胶囊筛选">
      <div class="row">
        <Pill v-for="f in filters" :key="f.k" :active="filter === f.k" @click="filter = f.k">{{ f.l }}</Pill>
      </div>
    </Panel>

    <Panel title="CtaButton 按钮">
      <div class="row">
        <CtaButton variant="accent">进入控制台 →</CtaButton>
        <CtaButton variant="ghost">编辑规则</CtaButton>
        <CtaButton variant="danger">↑ 升级故障</CtaButton>
        <CtaButton variant="accent" disabled>禁用态</CtaButton>
      </div>
    </Panel>
  </div>
</template>

<style scoped>
.sg { padding: 28px 32px; display: flex; flex-direction: column; gap: 18px; min-height: 100%; }
h1 { font-family: var(--font-head); font-weight: 600; font-size: 22px; margin: 0; color: var(--tx-1); }
.lead { margin: 0 0 4px; color: var(--tx-4); font-size: 12.5px; max-width: 720px; }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; }
.cell { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--tx-3); }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 13px; }
</style>
