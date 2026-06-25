import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Triage from './views/Triage.vue'
import Styleguide from './views/Styleguide.vue'
import './theme/tokens.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/triage' },
    { path: '/triage', component: Triage, meta: { title: '巡检分诊' } },
    { path: '/styleguide', component: Styleguide, meta: { title: 'Styleguide' } },
  ],
})

createApp(App).use(createPinia()).use(router).mount('#app')
