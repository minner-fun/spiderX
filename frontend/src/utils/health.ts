// 四层健康信号判定：把 Run.signals 翻译成 L1–L4 的[层/信号/当前值/判定]。
// 判定语义对齐设计纲要 §5：①②③任一异常=🔴；①②③正常且④=0=🟡；④>0=🟢；关键层 null=⚪。
import type { Signals, HealthStatus, DotState } from '../types'

export interface SignalRow {
  layer: string      // L1 HTTP …
  name: string       // 信号名
  value: string      // 当前值（已格式化）
  verdict: DotState  // 判定色态
  note: string       // 判定文案
}

const fmtPct = (v: number | null) => (v === null || v === undefined ? '未上报' : `${(v * 100).toFixed(0)}%`)

export function signalLayers(sig: Signals | null | undefined): SignalRow[] {
  const s: Signals = sig ?? {
    http_status: null, list_rows: null, field_fill_rate: null,
    dedup_new: null, duplicate: null, missing_rate: null, watermark_hit: null,
  }

  // L1 HTTP
  const l1: SignalRow = { layer: 'L1 · HTTP', name: '列表页状态码',
    value: s.http_status === null ? '未上报' : String(s.http_status),
    verdict: 'unknown', note: '' }
  if (s.http_status === null) { l1.verdict = 'unknown'; l1.note = '未上报' }
  else if (s.http_status === 200) { l1.verdict = 'green'; l1.note = '正常' }
  else { l1.verdict = 'red'; l1.note = `HTTP ${s.http_status} · 非 200` }

  // L2 列表解析
  const l2: SignalRow = { layer: 'L2 · 列表解析', name: 'list selector 命中行数',
    value: s.list_rows === null ? '未上报' : String(s.list_rows), verdict: 'unknown', note: '' }
  if (s.list_rows === null) { l2.verdict = 'unknown'; l2.note = '未上报' }
  else if (s.list_rows > 0) { l2.verdict = 'green'; l2.note = '正常命中' }
  else { l2.verdict = 'red'; l2.note = '命中 0 行 · 结构故障' }

  // L3 详情解析
  const l3: SignalRow = { layer: 'L3 · 详情解析', name: '必填字段抽到率',
    value: fmtPct(s.field_fill_rate), verdict: 'unknown', note: '' }
  if (s.field_fill_rate === null || s.field_fill_rate === undefined) {
    l3.verdict = s.list_rows === 0 ? 'red' : 'unknown'
    l3.note = s.list_rows === 0 ? '列表已挂 · 无从抽取' : '未上报'
  } else if (s.field_fill_rate >= 0.8) { l3.verdict = 'green'; l3.note = '正常' }
  else { l3.verdict = 'red'; l3.note = '抽取率偏低 · 详情模板挂' }

  // L4 数据
  const l4: SignalRow = { layer: 'L4 · 数据', name: '去重后新增条数',
    value: s.dedup_new === null ? '未上报' : String(s.dedup_new), verdict: 'unknown', note: '' }
  if (s.dedup_new === null) { l4.verdict = 'unknown'; l4.note = '未上报' }
  else if (s.dedup_new > 0) { l4.verdict = 'green'; l4.note = '持续出数据' }
  else { l4.verdict = 'yellow'; l4.note = '无新增 · 待确认真没数据' }

  return [l1, l2, l3, l4]
}

export function conclusion(h: HealthStatus): { state: DotState; text: string } {
  switch (h) {
    case 'structural_fail':
      return { state: 'red', text: 'HTTP 正常但列表/详情层异常 → 网站改版结构故障，需改配置（非"没数据"）。' }
    case 'data_dry':
      return { state: 'yellow', text: '前三层正常但去重后新增 = 0 多日 → 真没数据（健康但干涸），待人工确认或压制。' }
    case 'healthy':
      return { state: 'green', text: '四层信号正常，持续去重后出数据。' }
    default:
      return { state: 'unknown', text: '关键层未上报（代码驱动未按契约回报四层信号）→ 健康未知。' }
  }
}
