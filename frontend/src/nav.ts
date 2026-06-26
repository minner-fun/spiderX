// 侧栏导航模型。badge 计数为 M1 占位（真实来自 M4 巡检汇总），标注 placeholder。
import type { DotState } from './types'

export interface NavItem {
  key: string
  label: string
  to: string
  icon: string
  // 该导航项"拥有"的路由前缀（高亮归属）：如 爬虫 拥有 /spiders/:id、/versions、/rules
  owns?: string[]
  badge?: { count: number; state: Extract<DotState, 'red' | 'yellow'> }
  milestone?: string // 标注未实装屏（M2~M4）
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

export const NAV: NavGroup[] = [
  {
    title: '监控',
    items: [
      { key: 'triage', label: '巡检分诊', to: '/triage', icon: '◎', badge: { count: 23, state: 'red' } },
      { key: 'realtime', label: '实时 · 节点', to: '/realtime', icon: '◷', milestone: 'M4' },
      { key: 'alerts', label: '告警 · 反爬', to: '/alerts', icon: '⚠', badge: { count: 7, state: 'yellow' }, milestone: 'M4' },
    ],
  },
  {
    title: '管理',
    items: [
      { key: 'spiders', label: '爬虫', to: '/spiders', icon: '◈', owns: ['/spiders'] },
      { key: 'schedule', label: '调度', to: '/schedule', icon: '▤', milestone: 'M3' },
      { key: 'rules', label: '数据 · 规则', to: '/data', icon: '✦', milestone: 'M2' },
      { key: 'authors', label: '作者 · 权限', to: '/authors', icon: '◍', milestone: 'M4' },
    ],
  },
]

/** 当前路由属于哪个导航项（按 to 前缀或 owns 前缀匹配，取最长匹配）。 */
export function activeNavKey(path: string): string {
  let best = ''
  let bestLen = -1
  for (const g of NAV) {
    for (const it of g.items) {
      const prefixes = [it.to, ...(it.owns || [])]
      for (const p of prefixes) {
        if ((path === p || path.startsWith(p + '/')) && p.length > bestLen) {
          best = it.key
          bestLen = p.length
        }
      }
    }
  }
  return best
}
