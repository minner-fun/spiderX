<script setup lang="ts">
// 规则编辑器（M2）三栏：页面预览(点选高亮→生成 selector) / 字段映射 / 抓取配置。
// 顶部 URL 栏 + 试运行 + 保存并试运行(生成新版本)。试运行产出真实四层信号。
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type DryRunResult } from '../api/client'
import type { Spider } from '../types'
import { domainLabel } from '../utils/format'
import { signalLayers } from '../utils/health'
import Panel from '../components/Panel.vue'
import CtaButton from '../components/CtaButton.vue'
import StatusDot from '../components/StatusDot.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const spider = ref<Spider | null>(null)
const url = ref('/api/fixtures/bid-list')
const FIELD_TYPES = ['text', 'date', 'money', 'int', 'area']

// 编辑单个 list processor（processors[0]）
interface Field { name: string; selector: string; type: string; attr?: string }
const proc = reactive<{ row_selector: string; fields: Field[]; url_reg: string }>({
  row_selector: '', fields: [], url_reg: '',
})
const incremental = ref<Record<string, unknown>>({})
const hooks = ref<unknown[]>([])
const restRules = ref<Record<string, unknown>>({}) // 保留 entries/sink 等不在三栏编辑的部分

// 预览
const previewHtml = ref('')
const previewStatus = ref<number | null>(null)
const loadingPreview = ref(false)
const picking = ref<'row' | number | null>(null)

// 试运行
const result = ref<DryRunResult | null>(null)
const running = ref(false)
const saving = ref(false)
const savedMsg = ref('')

// 代码/可视化切换
const codeMode = ref(false)
const codeText = ref('')

const layers = computed(() => signalLayers(result.value?.signals))

function buildRules(): Record<string, unknown> {
  return {
    ...restRules.value,
    processors: [{
      url_reg: proc.url_reg || undefined, type: 'list',
      row_selector: proc.row_selector,
      fields: proc.fields.map(f => ({ name: f.name, selector: f.selector, type: f.type, ...(f.attr ? { attr: f.attr } : {}) })),
    }],
    incremental: incremental.value,
    sink: restRules.value.sink,
  }
}

function loadFromRules(rules: Record<string, unknown>) {
  const procs = (rules.processors as any[]) || []
  const p = procs.find(x => x.type === 'list') || procs[0] || {}
  proc.row_selector = p.row_selector || ''
  proc.url_reg = p.url_reg || ''
  proc.fields = (p.fields || []).map((f: any) => ({ name: f.name, selector: f.selector, type: f.type || 'text', attr: f.attr }))
  incremental.value = (rules.incremental as Record<string, unknown>) || {}
  const { processors, incremental: _i, ...rest } = rules
  restRules.value = rest
}

async function loadPreview() {
  loadingPreview.value = true
  try {
    const r = await api.fetchPage(url.value)
    previewStatus.value = r.status
    previewHtml.value = r.status === 200 ? injectPicker(r.html) : ''
  } finally { loadingPreview.value = false }
}

function injectPicker(html: string): string {
  const script = `
<style id="__pk">*{cursor:crosshair!important}
.__hl{outline:2px solid #4cc9e0!important;outline-offset:1px;background:rgba(76,201,224,.13)!important}</style>
<script>(function(){var last;
function leaf(el){var t=el.tagName.toLowerCase();var c=(el.getAttribute('class')||'').trim().split(/\\s+/).filter(function(x){return x&&x!=='__hl';});return c.length?t+'.'+c.join('.'):t;}
document.addEventListener('mouseover',function(e){if(last)last.classList.remove('__hl');last=e.target;if(last.classList)last.classList.add('__hl');},true);
document.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();
var el=e.target;var attrs=[];if(el.attributes)for(var i=0;i<el.attributes.length;i++)attrs.push(el.attributes[i].name);
parent.postMessage({__spiderx:true,selector:leaf(el),attrs:attrs},'*');},true);
})();<\/script>`
  return html.includes('</body>') ? html.replace('</body>', script + '</body>') : html + script
}

function onMessage(e: MessageEvent) {
  const d = e.data
  if (!d || !d.__spiderx || picking.value === null) return
  if (picking.value === 'row') {
    proc.row_selector = d.selector
  } else {
    const f = proc.fields[picking.value as number]
    if (f) {
      f.selector = d.selector
      if (d.attrs?.includes('href') && !f.attr && f.name.match(/link|url|href/i)) f.attr = 'href'
    }
  }
  picking.value = null
}

function addField() { proc.fields.push({ name: `field_${proc.fields.length + 1}`, selector: '', type: 'text' }) }
function removeField(i: number) { proc.fields.splice(i, 1) }

async function dryRun() {
  running.value = true; savedMsg.value = ''
  try { result.value = await api.dryRun(url.value, buildRules()) }
  finally { running.value = false }
}

async function saveAndRun() {
  saving.value = true; savedMsg.value = ''
  try {
    const ver = await api.saveRules(id.value, { rules: buildRules(), incremental: incremental.value, hooks: hooks.value, change_msg: '规则编辑器保存并试运行' })
    await dryRun()  // dryRun 会清 savedMsg，故消息在其后设置
    savedMsg.value = `已保存为 v${ver.version}（线上）`
  } finally { saving.value = false }
}

async function resetDefault() {
  const def = await api.defaultRules()
  loadFromRules(def)
  await loadPreview()
}

function toggleCode() {
  if (!codeMode.value) codeText.value = JSON.stringify(buildRules(), null, 2)
  else {
    try { loadFromRules(JSON.parse(codeText.value)) } catch { /* 忽略非法 JSON */ }
  }
  codeMode.value = !codeMode.value
}

onMounted(async () => {
  window.addEventListener('message', onMessage)
  try {
    spider.value = await api.getSpider(id.value)
    if (spider.value?.domain === 'ic') url.value = '/api/fixtures/ic-list'
    const r = await api.getRules(id.value)
    if (r.rules && Object.keys(r.rules).length) loadFromRules(r.rules)
    else loadFromRules(await api.defaultRules())
    incremental.value = r.incremental || incremental.value
    hooks.value = r.hooks || []
  } catch { loadFromRules(await api.defaultRules()) }
  await loadPreview()
  await dryRun()
})
onUnmounted(() => window.removeEventListener('message', onMessage))
watch(id, () => location.reload())
</script>

<template>
  <div class="page">
    <div class="crumb mono">
      <RouterLink to="/spiders" class="bk">爬虫</RouterLink> /
      <RouterLink :to="`/spiders/${id}`" class="bk">{{ spider?.name || '详情' }}</RouterLink> / <span>规则编辑器</span>
    </div>

    <!-- URL 栏 + 操作 -->
    <div class="urlbar">
      <span class="lbl mono">URL</span>
      <input v-model="url" class="url mono" placeholder="/api/fixtures/bid-list 或真实 https://…" @keyup.enter="loadPreview" />
      <CtaButton variant="ghost" @click="loadPreview">{{ loadingPreview ? '加载中…' : '加载页面' }}</CtaButton>
      <span class="grow" />
      <button class="codetoggle mono" :class="{ on: codeMode }" @click="toggleCode">{{ codeMode ? '可视化' : '代码/钩子' }}</button>
      <CtaButton variant="ghost" :disabled="running" @click="dryRun">{{ running ? '试运行中…' : '▶ 试运行' }}</CtaButton>
      <CtaButton variant="accent" :disabled="saving" @click="saveAndRun">{{ saving ? '保存中…' : '保存并试运行' }}</CtaButton>
    </div>
    <div v-if="savedMsg" class="saved mono">✓ {{ savedMsg }}</div>

    <!-- 代码模式 -->
    <Panel v-if="codeMode" title="规则 JSON（代码模式）" subtitle="编辑后切回可视化生效">
      <textarea v-model="codeText" class="code mono" spellcheck="false" />
    </Panel>

    <!-- 三栏 -->
    <div v-else class="cols">
      <!-- 页面预览 -->
      <Panel title="页面预览" :subtitle="previewStatus ? `HTTP ${previewStatus}` : ''">
        <template #actions>
          <span v-if="picking !== null" class="pickhint mono">点选元素中… <button class="cancel" @click="picking = null">取消</button></span>
        </template>
        <div class="previewwrap">
          <div v-if="loadingPreview" class="pvstate mono">加载中…</div>
          <div v-else-if="previewStatus !== 200" class="pvstate err mono">无法加载页面（HTTP {{ previewStatus }}）</div>
          <iframe v-else class="iframe" :srcdoc="previewHtml" sandbox="allow-scripts" />
        </div>
        <div class="pickrow">
          <span class="mono pl">行容器 row_selector</span>
          <input v-model="proc.row_selector" class="sel mono" placeholder="div.notice-item" />
          <button class="pick" :class="{ on: picking === 'row' }" @click="picking = picking === 'row' ? null : 'row'">拾取</button>
        </div>
      </Panel>

      <!-- 字段映射 -->
      <Panel title="字段映射" :subtitle="`${proc.fields.length} 字段`">
        <template #actions><button class="addf mono" @click="addField">+ 字段</button></template>
        <div v-if="!proc.fields.length" class="empty mono">点「+ 字段」添加，或在预览中拾取</div>
        <div v-for="(f, i) in proc.fields" :key="i" class="field">
          <div class="frow">
            <input v-model="f.name" class="fname mono" placeholder="字段名" />
            <select v-model="f.type" class="ftype mono">
              <option v-for="t in FIELD_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
            <button class="rmf" @click="removeField(i)">✕</button>
          </div>
          <div class="frow">
            <input v-model="f.selector" class="fsel mono" placeholder="selector（相对行）" />
            <button class="pick sm" :class="{ on: picking === i }" @click="picking = picking === i ? null : i">拾取</button>
          </div>
          <input v-if="f.attr !== undefined || f.name.match(/link|url/i)" v-model="f.attr" class="fattr mono" placeholder="attr（如 href，留空取文本）" />
        </div>
      </Panel>

      <!-- 抓取配置 + 试运行结果 -->
      <div class="rightcol">
        <Panel title="抓取配置">
          <div class="cfg">
            <label class="cfgrow"><span class="ck mono">增量字段</span>
              <input :value="incremental.field || ''" class="ci mono" @input="incremental.field = ($event.target as HTMLInputElement).value" placeholder="pub_time" /></label>
            <label class="cfgrow"><span class="ck mono">水位窗口</span>
              <input :value="incremental.window || ''" class="ci mono" @input="incremental.window = ($event.target as HTMLInputElement).value" placeholder="3d" /></label>
            <label class="cfgrow"><span class="ck mono">代码钩子</span>
              <span class="hookv mono">{{ hooks.length ? hooks.join(', ') : '无（配置驱动）' }}</span></label>
            <button class="reset mono" @click="resetDefault">重置为默认规则模板</button>
          </div>
        </Panel>

        <Panel title="试运行结果" :subtitle="result ? `${result.record_count} 条` : ''">
          <div v-if="!result" class="empty mono">点「试运行」抓首页验证规则</div>
          <template v-else>
            <div v-if="result.error" class="rerr mono">⚠ {{ result.error }}</div>
            <div class="siglist">
              <div v-for="l in layers" :key="l.layer" class="sigitem">
                <StatusDot :state="l.verdict" :size="7" />
                <span class="sl mono">{{ l.layer }}</span>
                <span class="sv mono" :class="l.verdict">{{ l.value }}</span>
                <span class="grow" />
                <span class="sn">{{ l.note }}</span>
              </div>
            </div>
            <div v-if="result.records.length" class="recs">
              <div class="recs-h mono">抽取样本（前 {{ Math.min(3, result.records.length) }} 条）</div>
              <pre v-for="(r, i) in result.records.slice(0, 3)" :key="i" class="rec mono">{{ JSON.stringify(r, null, 1) }}</pre>
            </div>
          </template>
        </Panel>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.crumb { font-size: 11.5px; color: var(--tx-5); }
.bk { color: var(--accent); }

.urlbar { display: flex; align-items: center; gap: 10px; background: var(--bg-panel); border: 1px solid var(--bd-panel); border-radius: var(--r-panel); padding: 10px 13px; }
.urlbar .lbl { font-size: 11px; color: var(--tx-muted); }
.url { flex: 1; min-width: 0; background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 8px 11px; color: var(--tx-1); font-size: 12px; outline: none; }
.url:focus { border-color: var(--accent); }
.grow { flex: 1; }
.codetoggle { background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: var(--r-control); color: var(--tx-3); font-size: 11.5px; padding: 8px 11px; cursor: pointer; }
.codetoggle.on { border-color: var(--accent); color: var(--accent); }
.saved { font-size: 11.5px; color: var(--green-text); }

.cols { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 12px; align-items: start; }
.rightcol { display: flex; flex-direction: column; gap: 12px; }

.previewwrap { height: 360px; background: #fff; border-radius: var(--r-card); overflow: hidden; }
.iframe { width: 100%; height: 100%; border: none; background: #fff; }
.pvstate { padding: 40px; text-align: center; color: var(--tx-5); }
.pvstate.err { color: var(--red-text); }
.pickhint { font-size: 11px; color: var(--accent); }
.cancel { background: none; border: none; color: var(--tx-5); cursor: pointer; font-size: 11px; text-decoration: underline; }

.pickrow, .frow { display: flex; align-items: center; gap: 8px; }
.pickrow { margin-top: 11px; }
.pl { font-size: 10.5px; color: var(--tx-muted); white-space: nowrap; }
.sel, .fsel { flex: 1; min-width: 0; background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 6px 9px; color: var(--accent); font-size: 11.5px; outline: none; }
.sel:focus, .fsel:focus { border-color: var(--accent); }
.pick { background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: 6px; color: var(--tx-3); font-size: 10.5px; padding: 5px 9px; cursor: pointer; white-space: nowrap; font-family: var(--font-mono); }
.pick.on, .pick:hover { border-color: var(--accent); color: var(--accent); }
.pick.sm { padding: 5px 8px; }

.addf, .reset { background: none; border: 1px solid var(--bd-control); border-radius: 6px; color: var(--tx-3); font-size: 11px; padding: 4px 9px; cursor: pointer; }
.addf:hover, .reset:hover { border-color: var(--accent); color: var(--accent); }
.empty { color: var(--tx-5); font-size: 12px; padding: 8px 0; }
.field { padding: 10px 0; border-top: 1px solid var(--bd-row); display: flex; flex-direction: column; gap: 7px; }
.field:first-of-type { border-top: none; }
.fname { flex: 1; background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 6px 9px; color: var(--tx-1); font-size: 12px; outline: none; }
.ftype { background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: var(--r-control); color: var(--tx-2); font-size: 11px; padding: 6px 7px; font-family: var(--font-mono); }
.rmf { background: none; border: none; color: var(--tx-weak); cursor: pointer; font-size: 13px; }
.rmf:hover { color: var(--red-text); }
.fattr { background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 5px 9px; color: var(--tx-3); font-size: 11px; outline: none; }

.cfg { display: flex; flex-direction: column; gap: 10px; }
.cfgrow { display: flex; align-items: center; gap: 10px; }
.ck { font-size: 11px; color: var(--tx-muted); width: 64px; }
.ci { flex: 1; background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 6px 9px; color: var(--tx-1); font-size: 11.5px; outline: none; }
.hookv { font-size: 11.5px; color: var(--tx-4); }
.reset { margin-top: 4px; align-self: flex-start; }

.rerr { font-size: 11.5px; color: var(--red-text); background: var(--red-bg); border: 1px solid var(--red-bd); border-radius: var(--r-card); padding: 7px 10px; margin-bottom: 10px; }
.siglist { display: flex; flex-direction: column; gap: 8px; }
.sigitem { display: flex; align-items: center; gap: 8px; font-size: 11.5px; }
.sl { color: var(--tx-3); white-space: nowrap; }
.sv { font-weight: 600; }
.sv.green { color: var(--green-text); } .sv.red { color: var(--red-text); } .sv.yellow { color: var(--yellow-text); } .sv.unknown { color: var(--tx-5); }
.sn { color: var(--tx-5); font-size: 10.5px; }
.recs { margin-top: 12px; }
.recs-h { font-size: 10.5px; color: var(--tx-muted); margin-bottom: 7px; }
.rec { margin: 0 0 7px; background: var(--bg-terminal); border-radius: var(--r-card); padding: 9px 11px; font-size: 10.5px; color: var(--tx-3); white-space: pre-wrap; line-height: 1.5; }

.code { width: 100%; min-height: 420px; background: var(--bg-terminal); border: none; border-radius: var(--r-card); color: var(--tx-2); font-size: 12px; line-height: 1.6; padding: 12px 14px; outline: none; resize: vertical; }
</style>
