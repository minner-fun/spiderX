// API 封装。同源 /api 由 vite 代理到 backend（见 vite.config）。
// M1 假登录：本地 token 写在 localStorage，请求带 Authorization（后端暂不校验）。
import type {
  Project, Spider, SpiderVersion, Run, Paginated, Priority,
} from '../types'

const TOKEN_KEY = 'spiderx_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function http<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
    ...opts,
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

function qs(params: Record<string, unknown>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

/** 列表接口兼容：后端可能返回数组（M0）或分页对象（M1）。 */
export function asItems<T>(res: T[] | { items: T[] }): T[] {
  return Array.isArray(res) ? res : res.items
}

export interface SpiderListQuery {
  health?: string
  status?: string
  owner?: string
  domain?: string
  q?: string
  page?: number
  page_size?: number
}

export const api = {
  health: () => http<{ status: string; db: boolean; redis: boolean }>('/health'),

  listProjects: () => http<Project[]>('/api/projects'),

  // 列表：后端补齐筛选/分页后返回 Paginated；当前后端若仍返回数组，listSpiders 做兼容。
  listSpiders: (pid: string, query: SpiderListQuery = {}) =>
    http<Paginated<Spider> | Spider[]>(`/api/projects/${pid}/spiders${qs({ ...query })}`),

  createSpider: (pid: string, body: { name: string; priority?: Priority; tags?: string[] }) =>
    http<Spider>(`/api/projects/${pid}/spiders`, { method: 'POST', body: JSON.stringify(body) }),

  getSpider: (sid: string) => http<Spider>(`/api/spiders/${sid}`),

  patchSpider: (sid: string, body: Partial<Pick<Spider, 'status' | 'priority'>>) =>
    http<Spider>(`/api/spiders/${sid}`, { method: 'PATCH', body: JSON.stringify(body) }),

  runSpider: (sid: string) => http<{ queued: boolean }>(`/api/spiders/${sid}/run`, { method: 'POST' }),

  listVersions: (sid: string) => http<SpiderVersion[]>(`/api/spiders/${sid}/versions`),

  diffVersions: (sid: string, from: number, to: number) =>
    http<{ from: number; to: number; lines: DiffLine[] }>(
      `/api/spiders/${sid}/versions/diff${qs({ from, to })}`,
    ),

  rollback: (sid: string, version: number) =>
    http<SpiderVersion>(`/api/spiders/${sid}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    }),

  listRuns: (sid: string, limit = 10) =>
    http<Run[]>(`/api/spiders/${sid}/runs${qs({ limit })}`),

  // —— M2 规则编辑器 / 引擎 ——
  getRules: (sid: string) => http<RulesPayload>(`/api/spiders/${sid}/rules`),

  saveRules: (sid: string, body: RulesPayload & { change_msg?: string }) =>
    http<SpiderVersion>(`/api/spiders/${sid}/rules`, { method: 'POST', body: JSON.stringify(body) }),

  defaultRules: () => http<Record<string, unknown>>('/api/engine/default-rules'),

  dryRun: (url: string, rules: Record<string, unknown>) =>
    http<DryRunResult>('/api/engine/dry-run', { method: 'POST', body: JSON.stringify({ url, rules }) }),

  fetchPage: (url: string) =>
    http<{ status: number; html: string }>('/api/engine/fetch-page', {
      method: 'POST', body: JSON.stringify({ url }),
    }),

  scheduleOverview: () => http<ScheduleOverview>('/api/schedule/overview'),
}

export interface ScheduleRow {
  spider_id: string
  spider_name: string
  domain: string
  cron: string
  queue: string
  enabled: boolean
  jitter_sec: number
  last_run_at: string | null
  next_run_at: string | null
  fires: number[]
}

export interface ScheduleOverview {
  schedules: ScheduleRow[]
  reconcile: { dispatched: number; started: number; completed: number; stuck: number; failed: number; dlq: number }
  queues: { name: string; depth: number }[]
  now: string
}

export interface RulesPayload {
  version?: number | null
  rules: Record<string, unknown>
  incremental: Record<string, unknown>
  hooks: unknown[]
}

export interface DryRunResult {
  http_status: number
  list_rows: number | null
  field_fill_rate: number | null
  record_count: number
  records: Record<string, unknown>[]
  signals: import('../types').Signals
  error: string | null
}

export interface DiffLine {
  op: 'add' | 'del' | 'chg' | 'ctx'
  text: string
}
