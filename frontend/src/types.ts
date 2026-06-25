// 域类型与枚举映射 —— 与 backend shared/enums.py 对齐。
// 健康三态色严格守恒（数据语义），执行态与健康态分离。

export type HealthStatus = 'healthy' | 'data_dry' | 'structural_fail' | 'unknown'
export type ExecStatus = 'running' | 'paused' | 'disabled' | 'failed'
export type Priority = 'P0' | 'P1' | 'P2'
export type Domain = 'bid' | 'ic' | 'ecommerce' | 'jobs' | 'other'
export type RunExecStatus = 'queued' | 'running' | 'success' | 'failed' | 'stopped'
export type DataOutcome = 'new' | 'dry' | 'na'

/** 状态灯/徽章的色态键（含品牌青）。健康三态映射到 red/yellow/green/unknown。 */
export type DotState = 'red' | 'yellow' | 'green' | 'unknown' | 'cyan'

export const HEALTH_TO_DOT: Record<HealthStatus, DotState> = {
  healthy: 'green',
  data_dry: 'yellow',
  structural_fail: 'red',
  unknown: 'unknown',
}

export const HEALTH_LABEL: Record<HealthStatus, string> = {
  healthy: '健康',
  data_dry: '数据干涸',
  structural_fail: '结构故障',
  unknown: '未上报',
}

export const HEALTH_GLYPH: Record<HealthStatus, string> = {
  healthy: '●',
  data_dry: '●',
  structural_fail: '●',
  unknown: '○',
}

export const EXEC_LABEL: Record<ExecStatus, string> = {
  running: '运行中',
  paused: '已暂停',
  disabled: '已停用',
  failed: '失败',
}

export const DOMAIN_LABEL: Record<Domain, string> = {
  bid: '招投标',
  ic: 'IC 元器件',
  ecommerce: '电商',
  jobs: '招聘',
  other: '其他',
}

/** 四层信号契约（Run.signals），缺层 = null = unknown。 */
export interface Signals {
  http_status: number | null
  list_rows: number | null
  field_fill_rate: number | null
  dedup_new: number | null
  duplicate: number | null
  missing_rate: number | null
  watermark_hit: boolean | null
}

export interface Project {
  id: string
  name: string
  env: string
  domain: Domain
}

export interface Spider {
  id: string
  project_id: string
  name: string
  status: ExecStatus
  health_status: HealthStatus
  priority: Priority
  contribution_pct: number
  is_core: boolean
  created_at: string
  // M1 详情/列表扩展字段（后端补齐后填充，前端容错可选）
  owner_name?: string | null
  domain?: Domain
  tags?: string[]
  cron?: string | null
  last_run_at?: string | null
  success_rate?: number | null
  current_version?: number | null
  signals?: Signals | null
}

export interface SpiderVersion {
  id: string
  spider_id: string
  version: number
  is_live: boolean
  author_name?: string | null
  change_msg: string
  created_at: string
  rules?: Record<string, unknown>
  incremental?: Record<string, unknown>
  hooks?: unknown[]
}

export interface Run {
  id: string
  spider_id: string
  exec_status: RunExecStatus
  data_outcome: DataOutcome
  signals: Signals
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  stats?: Record<string, unknown>
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
