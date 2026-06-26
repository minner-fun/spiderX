<script setup lang="ts">
// App Shell：侧栏（品牌 + 监控/管理组 + 值班用户）+ 顶栏（项目/env/⌘K/巡检/告警）。
import { computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { NAV, activeNavKey } from '../nav'
import { useAuth } from '../stores/auth'
import { useSession } from '../stores/session'
import StatusDot from '../components/StatusDot.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const session = useSession()

const activeKey = computed(() => activeNavKey(route.path))
const pageTitle = computed(() => (route.meta.title as string) || '')

onMounted(() => session.load())

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar hf-grid">
      <div class="brand">
        <span class="logo" />
        <div class="brand-tx">
          <div class="bname">ARACHNE</div>
          <div class="bsub mono">CRAWL CONTROL</div>
        </div>
      </div>

      <nav class="nav">
        <div v-for="g in NAV" :key="g.title" class="navgroup">
          <div class="gtitle mono">{{ g.title }}</div>
          <RouterLink
            v-for="it in g.items" :key="it.key" :to="it.to"
            class="navitem" :class="{ active: activeKey === it.key }"
          >
            <span class="ico">{{ it.icon }}</span>
            <span class="lbl">{{ it.label }}</span>
            <span v-if="it.badge" class="count" :class="it.badge.state">{{ it.badge.count }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="duty">
        <div class="avatar">{{ auth.displayName.slice(0, 1).toUpperCase() }}</div>
        <div class="duty-tx">
          <div class="dname">{{ auth.displayName }}</div>
          <div class="drole mono">值班 · maintainer</div>
        </div>
        <button class="logout mono" title="退出登录" @click="logout">⎋</button>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <button class="proj">
          <StatusDot state="cyan" :size="7" />
          <span class="pname">{{ session.current?.name || '加载中…' }}</span>
          <span class="caret">▾</span>
        </button>
        <span class="env mono" :class="{ prod: session.env === 'prod' }">{{ session.env }}</span>

        <div class="search mono">
          <span class="sk">⌘K</span>
          <span class="sp">搜索爬虫 / 域名 / Run…</span>
        </div>

        <span class="grow" />

        <div class="insp">
          <StatusDot state="green" live :size="7" />
          <span class="insp-tx mono">巡检 12:00 · 每小时</span>
        </div>
        <button class="bell">
          <span class="bico">◔</span>
          <span class="bdot" />
        </button>
      </header>

      <main class="content">
        <div class="content-inner">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell { display: flex; height: 100%; }

/* —— 侧栏 —— */
.sidebar {
  width: var(--sidebar-w); flex: none; display: flex; flex-direction: column;
  background: linear-gradient(180deg, var(--bg-sidebar-1), var(--bg-sidebar-2));
  border-right: 1px solid var(--bd-divider); padding: 14px 12px 12px;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 6px 16px; }
.logo {
  width: 22px; height: 22px; flex: none; transform: rotate(45deg); border-radius: 5px;
  background: var(--accent-grad); box-shadow: var(--accent-glow);
}
.bname { font-family: var(--font-head); font-weight: 600; font-size: 15px; letter-spacing: .5px; color: var(--tx-1); }
.bsub { font-size: 9.5px; letter-spacing: 1.5px; color: var(--tx-muted); margin-top: 1px; }

.nav { display: flex; flex-direction: column; gap: 16px; margin-top: 4px; }
.gtitle { font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--tx-weak); padding: 0 8px 6px; }
.navgroup { display: flex; flex-direction: column; gap: 2px; }
.navitem {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--r-control);
  color: var(--tx-4); border-left: 2px solid transparent; position: relative;
  font-size: 13px; transition: background .12s, color .12s;
}
.navitem:hover { background: var(--bg-inset); color: var(--tx-2); }
.navitem.active {
  background: var(--accent-select-bg); color: var(--tx-1);
  border-left-color: var(--accent); font-weight: 500;
}
.navitem.active .ico { color: var(--accent); }
.ico { width: 16px; text-align: center; font-size: 13px; color: var(--tx-5); flex: none; }
.lbl { flex: 1; }
.count {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600; line-height: 1;
  padding: 2px 6px; border-radius: 9px; flex: none;
}
.count.red { color: var(--red-text); background: var(--red-bg); border: 1px solid var(--red-bd); }
.count.yellow { color: var(--yellow-text); background: var(--yellow-bg); border: 1px solid var(--yellow-bd); }

.duty {
  margin-top: auto; display: flex; align-items: center; gap: 9px;
  padding: 10px 8px 4px; border-top: 1px solid var(--bd-divider);
}
.avatar {
  width: 28px; height: 28px; border-radius: 8px; flex: none;
  display: grid; place-items: center; font-family: var(--font-head); font-weight: 600; font-size: 13px;
  color: var(--accent-on); background: var(--accent-grad);
}
.duty-tx { flex: 1; min-width: 0; }
.dname { font-size: 12.5px; color: var(--tx-2); }
.drole { font-size: 9.5px; color: var(--tx-muted); margin-top: 1px; }
.logout { background: none; border: none; color: var(--tx-weak); cursor: pointer; font-size: 14px; padding: 4px; }
.logout:hover { color: var(--accent); }

/* —— 主区 —— */
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar {
  height: var(--topbar-h); flex: none; display: flex; align-items: center; gap: 12px;
  padding: 0 18px; border-bottom: 1px solid var(--bd-divider);
  background: color-mix(in srgb, var(--bg-topbar) 90%, transparent);
  backdrop-filter: blur(6px); position: sticky; top: 0; z-index: 10;
}
.proj {
  display: inline-flex; align-items: center; gap: 8px; cursor: pointer;
  background: var(--bg-chip); border: 1px solid var(--bd-control); border-radius: var(--r-control);
  padding: 6px 10px; color: var(--tx-2); font-size: 12.5px;
}
.proj:hover { border-color: var(--bd-accent); }
.caret { color: var(--tx-weak); font-size: 10px; }
.env {
  font-size: 11px; color: var(--tx-4); border: 1px solid var(--bd-control);
  border-radius: var(--r-control); padding: 4px 9px; text-transform: lowercase;
}
.env.prod { color: var(--yellow-text); border-color: var(--yellow-bd); background: var(--yellow-bg); }

.search {
  display: inline-flex; align-items: center; gap: 8px; min-width: 240px;
  background: var(--bg-input); border: 1px solid var(--bd-control); border-radius: var(--r-control);
  padding: 6px 10px; color: var(--tx-weak); font-size: 12px;
}
.sk { color: var(--tx-5); border: 1px solid var(--bd-control); border-radius: 4px; padding: 1px 5px; font-size: 10px; }
.grow { flex: 1; }
.insp { display: inline-flex; align-items: center; gap: 7px; }
.insp-tx { font-size: 11px; color: var(--tx-4); }
.bell { position: relative; background: none; border: none; cursor: pointer; color: var(--tx-3); font-size: 16px; padding: 4px; }
.bell:hover { color: var(--tx-1); }
.bdot {
  position: absolute; top: 3px; right: 2px; width: 6px; height: 6px; border-radius: 50%;
  background: var(--red-dot); box-shadow: 0 0 6px var(--red-dot);
}

.content { flex: 1; overflow: auto; }
.content-inner { max-width: var(--content-max); margin: 0 auto; padding: 20px 24px 40px; }
</style>
