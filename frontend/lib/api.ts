// Cliente da API local (FastAPI em :8010, acessado via rewrite /api -> backend).

const BASE = '/api'

export type JobStatus = 'pendente' | 'rodando' | 'concluido' | 'erro'
export type AssetStatus = 'rascunho' | 'aprovado' | 'agendado' | 'publicado'

export interface Job {
  id: string
  workspace_id: string
  pilar: string
  formato: string
  tema: string | null
  turno: string | null
  status: JobStatus
  erro_msg: string | null
  criado_em: string
  atualizado_em: string
}

export interface Asset {
  id: string
  job_id: string
  workspace_id: string
  tipo: string
  caminho: string | null
  status: AssetStatus
  metadados: Record<string, unknown>
  criado_em: string
}

export interface CriarJobInput {
  workspace_id?: string
  pilar: string
  formato: string
  tema?: string | null
  turno?: string | null
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    cache: 'no-store',
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body?.detail || detail
    } catch {
      /* corpo não-JSON */
    }
    throw new Error(`${res.status} — ${detail}`)
  }
  return res.json() as Promise<T>
}

// Paths SEM barra final: o rewrite do Next (next.config.mjs) mapeia
// /api/jobs -> backend /jobs/ etc., preservando a barra que o FastAPI exige.
export function criarJob(input: CriarJobInput) {
  return req<{ job_id: string; status: JobStatus }>('/jobs', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: 'focusclear', ...input }),
  })
}

export function getJob(id: string) {
  return req<Job>(`/jobs/${id}`)
}

export function listarJobs() {
  return req<Job[]>('/jobs')
}

export function listarAssets() {
  return req<Asset[]>('/assets')
}

export function atualizarStatusAsset(id: string, status: AssetStatus) {
  return req<{ ok: boolean; status: AssetStatus }>(
    `/assets/${id}/status?status=${encodeURIComponent(status)}`,
    { method: 'PATCH' },
  )
}

// URL do PNG do slide (servido por file path pelo backend via rewrite).
export function imagemAssetUrl(id: string): string {
  return `${BASE}/assets/${id}/image`
}
