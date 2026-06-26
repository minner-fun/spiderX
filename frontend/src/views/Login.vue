<script setup lang="ts">
// 登录页（M1 假登录）：左品牌/实时 mini 控制台，右表单。填任意 → set token → 进控制台。
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../stores/auth'
import StatusDot from '../components/StatusDot.vue'
import CtaButton from '../components/CtaButton.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const account = ref('ops@spiderx.team')
const password = ref('')
const showPwd = ref(false)
const keep = ref(true)
const env = ref('prod')
const submitting = ref(false)
const err = ref('')

// mini 控制台滚动日志（纯装饰）
const logs = ref<string[]>([])
const SEED = [
  ['OK', '中国政府采购网-中央 · 新增 142 条'],
  ['WARN', '深圳交易集团 · list_rows=0 → 结构故障'],
  ['INFO', '巡检 12:00 启动 · 2,000 站'],
  ['OK', '广东省采购网 · 命中水位正常停止'],
  ['ERR', 'IC-Digikey · HTTP 403 封禁'],
  ['INFO', '代理池 30 IP 滚动刷新'],
]
let timer: number | undefined
let i = 0
onMounted(() => {
  for (let k = 0; k < 4; k++) logs.value.push(fmt(SEED[k % SEED.length]))
  timer = window.setInterval(() => {
    logs.value.unshift(fmt(SEED[i++ % SEED.length]))
    if (logs.value.length > 6) logs.value.pop()
  }, 2200)
})
onUnmounted(() => clearInterval(timer))
function fmt([lvl, msg]: string[]) {
  const t = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  return `${t} [${lvl}] ${msg}`
}
function lvlClass(line: string) {
  if (line.includes('[OK]')) return 'ok'
  if (line.includes('[WARN]')) return 'warn'
  if (line.includes('[ERR]')) return 'err'
  return 'info'
}

function submit() {
  err.value = ''
  if (!account.value.trim()) { err.value = '请输入账号'; return }
  if (!password.value) { err.value = '请输入密码'; return }
  submitting.value = true
  setTimeout(() => {
    auth.login(account.value.trim())
    const to = (route.query.redirect as string) || '/spiders'
    router.replace(to)
  }, 350)
}
</script>

<template>
  <div class="login">
    <!-- 左：品牌 / 实时 mini 控制台 -->
    <section class="left hf-grid">
      <div class="corner hf-corner-glow" />
      <div class="scan" />
      <div class="left-inner">
        <div class="brand">
          <span class="logo" />
          <div>
            <div class="bname">ARACHNE</div>
            <div class="bsub mono">SPIDERX · CRAWL CONTROL</div>
          </div>
        </div>

        <h1 class="slogan">2000 个爬虫，<br />一眼看清谁挂了、谁没数据。</h1>
        <p class="tag">配置即数据 · Run 记录当真相源 · 自动分诊。把「人盯人」换成「四层信号」。</p>

        <div class="mini">
          <div class="mini-h">
            <StatusDot state="green" live :size="7" />
            <span class="mono">LIVE · 巡检实时流</span>
            <span class="grow" />
            <span class="mono ts">每小时</span>
          </div>
          <div class="counts">
            <div class="c"><span class="n num red">23</span><span class="l">结构故障</span></div>
            <div class="c"><span class="n num yellow">41</span><span class="l">数据干涸</span></div>
            <div class="c"><span class="n num green">1,936</span><span class="l">健康</span></div>
          </div>
          <div class="feed mono">
            <div v-for="(l, k) in logs" :key="k" class="line" :class="lvlClass(l)">{{ l }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 右：表单 -->
    <section class="right">
      <div class="form">
        <div class="fhead">
          <div class="ftitle">进入控制台</div>
          <div class="fsub">内部工程团队 · 单点登录或账号密码</div>
        </div>

        <div class="sso">
          <button class="sso-btn"><span class="sg">◆</span> 飞书登录</button>
          <button class="sso-btn"><span class="sg">◈</span> 企业微信</button>
        </div>
        <div class="divider"><span>或使用账号密码</span></div>

        <form @submit.prevent="submit">
          <label class="field">
            <span class="flabel">账号</span>
            <input v-model="account" class="input mono" type="text" autocomplete="username" placeholder="name@spiderx.team" />
          </label>
          <label class="field">
            <span class="flabel">密码</span>
            <div class="pwd">
              <input v-model="password" class="input mono" :type="showPwd ? 'text' : 'password'"
                autocomplete="current-password" placeholder="••••••••" />
              <button type="button" class="eye" @click="showPwd = !showPwd">{{ showPwd ? '隐藏' : '显示' }}</button>
            </div>
          </label>

          <div class="row">
            <label class="keep"><input v-model="keep" type="checkbox" /> 保持登录</label>
            <span class="grow" />
            <label class="envsel mono">
              env
              <select v-model="env">
                <option value="prod">prod</option>
                <option value="staging">staging</option>
                <option value="dev">dev</option>
              </select>
            </label>
          </div>

          <div v-if="err" class="err mono">⚠ {{ err }}</div>

          <CtaButton variant="accent" type="submit" :disabled="submitting" class="submit">
            {{ submitting ? '校验中…' : '进入控制台 →' }}
          </CtaButton>
        </form>

        <p class="twofa mono">受 2FA 保护 · 仅限内网 · M1 为本地假登录</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login { display: flex; height: 100%; background: var(--bg-page); }

/* 左 */
.left { position: relative; flex: 1; overflow: hidden; border-right: 1px solid var(--bd-divider); }
.corner { position: absolute; inset: 0; pointer-events: none; }
.scan {
  position: absolute; left: 0; right: 0; height: 2px; top: 0;
  background: linear-gradient(90deg, transparent, #4cc9e055, transparent);
  animation: hfscan 5s linear infinite; pointer-events: none;
}
.left-inner { position: relative; height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 0 7% 0 8%; max-width: 620px; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 38px; }
.logo { width: 26px; height: 26px; transform: rotate(45deg); border-radius: 6px; background: var(--accent-grad); box-shadow: var(--accent-glow); }
.bname { font-family: var(--font-head); font-weight: 600; font-size: 17px; letter-spacing: .5px; }
.bsub { font-size: 9.5px; letter-spacing: 1.5px; color: var(--tx-muted); margin-top: 2px; }
.slogan { font-family: var(--font-head); font-weight: 600; font-size: 30px; line-height: 1.35; margin: 0 0 14px; color: var(--tx-1); }
.tag { font-size: 13px; color: var(--tx-4); max-width: 420px; line-height: 1.7; margin: 0 0 34px; }

.mini { background: color-mix(in srgb, var(--bg-panel) 80%, transparent); border: 1px solid var(--bd-panel); border-radius: var(--r-panel); padding: 14px; max-width: 440px; backdrop-filter: blur(4px); }
.mini-h { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--tx-4); margin-bottom: 13px; }
.mini-h .grow { flex: 1; }
.ts { color: var(--tx-weak); }
.counts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 13px; }
.c { display: flex; flex-direction: column; gap: 3px; padding: 9px 11px; background: var(--bg-inset); border: 1px solid var(--bd-card); border-radius: var(--r-card); }
.n { font-size: 21px; font-weight: 600; line-height: 1; }
.n.red { color: var(--red-text); } .n.yellow { color: var(--yellow-text); } .n.green { color: var(--green-text); }
.l { font-size: 10.5px; color: var(--tx-muted); }
.feed { background: var(--bg-terminal); border: 1px solid var(--bd-divider); border-radius: var(--r-card); padding: 9px 11px; height: 96px; overflow: hidden; }
.line { font-size: 10.5px; line-height: 1.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.line.ok { color: var(--green-text); } .line.warn { color: var(--yellow-text); } .line.err { color: var(--red-text); } .line.info { color: var(--tx-5); }

/* 右 */
.right { width: var(--login-right-w); flex: none; display: flex; align-items: center; justify-content: center; padding: 24px; }
.form { width: 100%; max-width: 360px; }
.fhead { margin-bottom: 22px; }
.ftitle { font-family: var(--font-head); font-weight: 600; font-size: 22px; color: var(--tx-1); }
.fsub { font-size: 12px; color: var(--tx-5); margin-top: 5px; }
.sso { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 18px; }
.sso-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; padding: 9px; background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: var(--r-control); color: var(--tx-2); font-size: 12.5px; cursor: pointer; }
.sso-btn:hover { border-color: var(--bd-accent); color: var(--tx-1); }
.sg { color: var(--accent); }
.divider { display: flex; align-items: center; gap: 12px; color: var(--tx-weak); font-size: 11px; margin: 0 0 18px; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--bd-divider); }
.field { display: block; margin-bottom: 14px; }
.flabel { display: block; font-size: 11.5px; color: var(--tx-4); margin-bottom: 6px; }
.input { width: 100%; background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control); padding: 9px 11px; color: var(--tx-1); font-size: 13px; outline: none; }
.input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px #4cc9e018; }
.pwd { position: relative; }
.pwd .input { padding-right: 52px; }
.eye { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--tx-5); font-size: 11px; cursor: pointer; font-family: var(--font-body); }
.eye:hover { color: var(--accent); }
.row { display: flex; align-items: center; margin: 4px 0 18px; }
.row .grow { flex: 1; }
.keep { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--tx-4); cursor: pointer; }
.envsel { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; color: var(--tx-5); }
.envsel select { background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: 6px; color: var(--tx-3); padding: 3px 6px; font-family: var(--font-mono); font-size: 11px; }
.err { color: var(--red-text); font-size: 11.5px; margin-bottom: 12px; }
.submit { width: 100%; justify-content: center; padding: 11px; font-size: 13px; }
.twofa { text-align: center; color: var(--tx-weak); font-size: 10.5px; margin-top: 18px; }

@media (max-width: 920px) { .left { display: none; } .right { width: 100%; } }
</style>
