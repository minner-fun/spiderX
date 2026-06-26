// 会话上下文 store：项目列表 + 当前项目 + env。供 AppShell 顶栏项目切换器使用。
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api/client'
import type { Project } from '../types'

export const useSession = defineStore('session', () => {
  const projects = ref<Project[]>([])
  const currentId = ref<string>(localStorage.getItem('spiderx_project') || '')
  const loaded = ref(false)

  const current = computed(() => projects.value.find(p => p.id === currentId.value) || projects.value[0] || null)
  const env = computed(() => current.value?.env ?? 'dev')

  async function load() {
    if (loaded.value) return
    projects.value = await api.listProjects()
    if (!currentId.value && projects.value.length) currentId.value = projects.value[0].id
    loaded.value = true
  }

  function select(id: string) {
    currentId.value = id
    localStorage.setItem('spiderx_project', id)
  }

  return { projects, currentId, current, env, loaded, load, select }
})
