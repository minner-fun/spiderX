import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Triage from './views/Triage.vue'
import './theme/tokens.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/triage' },
    { path: '/triage', component: Triage, meta: { title: '巡检分诊' } },
  ],
})

createApp(App).use(createPinia()).use(router).mount('#app')
