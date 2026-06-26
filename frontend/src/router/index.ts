// 路由 + auth guard。/login 不套 AppShell；其余屏套 AppShell。
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/client'
import AppShell from '../layouts/AppShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true, title: '登录' } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', redirect: '/spiders' },
        { path: 'triage', component: () => import('../views/Triage.vue'), meta: { title: '巡检分诊' } },
        { path: 'spiders', component: () => import('../views/Spiders.vue'), meta: { title: '爬虫' } },
        { path: 'spiders/:id', component: () => import('../views/SpiderDetail.vue'), meta: { title: '爬虫详情' } },
        { path: 'spiders/:id/versions', component: () => import('../views/Versions.vue'), meta: { title: '版本管理' } },
        { path: 'spiders/:id/rules', component: () => import('../views/Rules.vue'), meta: { title: '规则编辑器' } },
        { path: 'realtime', component: () => import('../views/Placeholder.vue'), meta: { title: '实时 · 节点', milestone: 'M4' } },
        { path: 'alerts', component: () => import('../views/Placeholder.vue'), meta: { title: '告警 · 反爬', milestone: 'M4' } },
        { path: 'schedule', component: () => import('../views/Schedule.vue'), meta: { title: '调度 · 对账' } },
        { path: 'data', component: () => import('../views/Placeholder.vue'), meta: { title: '数据 · 规则', milestone: 'M2' } },
        { path: 'authors', component: () => import('../views/Placeholder.vue'), meta: { title: '作者 · 权限', milestone: 'M4' } },
        { path: 'styleguide', component: () => import('../views/Styleguide.vue'), meta: { title: 'Styleguide' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/spiders' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!getToken()) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

export default router
