// 认证 store（M1 假登录）：本地 token + 用户名，真 SSO/2FA 后置。
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken, setToken, clearToken } from '../api/client'

export const useAuth = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const account = ref<string>(localStorage.getItem('spiderx_account') || '')

  const isAuthed = computed(() => !!token.value)

  // 显示名：账号 @ 前缀，兜底 ops
  const displayName = computed(() => account.value.split('@')[0] || 'ops')

  function login(acct: string) {
    const t = `fake.${btoa(unescape(encodeURIComponent(acct))).slice(0, 24)}.m1`
    setToken(t)
    localStorage.setItem('spiderx_account', acct)
    token.value = t
    account.value = acct
  }

  function logout() {
    clearToken()
    localStorage.removeItem('spiderx_account')
    token.value = null
    account.value = ''
  }

  return { token, account, isAuthed, displayName, login, logout }
})
