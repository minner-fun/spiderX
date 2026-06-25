// 极简 API 封装（M0），同源 /api 由 vite 代理到 backend
async function http<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  health: () => http<{ status: string; db: boolean; redis: boolean }>('/health'),
  listProjects: () => http<any[]>('/api/projects'),
  listSpiders: (pid: string) => http<any[]>(`/api/projects/${pid}/spiders`),
  createSpider: (pid: string, name: string) =>
    http<any>(`/api/projects/${pid}/spiders`, { method: 'POST', body: JSON.stringify({ name }) }),
  runSpider: (sid: string) =>
    http<any>(`/api/spiders/${sid}/run`, { method: 'POST' }),
}
