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

// ── Pilares ──────────────────────────────────────────────────────────────
export interface Pilar {
  id: number
  workspace_id: string
  nome: string
  status: string // ativo | planejado | desativado
  config: Record<string, unknown>
}

export function listarPilares() {
  return req<Pilar[]>('/pilares')
}

export function atualizarPilar(
  id: number,
  patch: { status?: string; config?: Record<string, unknown> },
) {
  return req<Pilar>(`/pilares/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
}

// ── Tendências ───────────────────────────────────────────────────────────
export interface Tendencia {
  id: number
  workspace_id: string
  pilar: string
  termo: string
  score: number
  data: string
}

export function listarTendencias() {
  return req<Tendencia[]>('/tendencias')
}

// ── Personagem ───────────────────────────────────────────────────────────
export interface Personagem {
  id: number
  workspace_id: string
  nome: string
  descricao: string
  tom_de_voz: string
  foto_ref: string | null
}

export function getPersonagem() {
  return req<Personagem>('/personagem')
}

export function salvarPersonagem(body: {
  nome: string
  descricao: string
  tom_de_voz: string
}) {
  return req<Personagem>('/personagem', { method: 'PUT', body: JSON.stringify(body) })
}

export function fotoPersonagemUrl(bust?: number): string {
  return `${BASE}/personagem/foto${bust ? `?t=${bust}` : ''}`
}

export async function uploadFotoPersonagem(file: File) {
  const form = new FormData()
  form.append('file', file)
  // sem Content-Type manual: o browser define o boundary do multipart
  const res = await fetch(`${BASE}/personagem/foto`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`${res.status} — upload falhou`)
  return res.json() as Promise<{ ok: boolean; foto_ref: string }>
}

// ── Integrações (.env, read-only) ────────────────────────────────────────
export interface Integracao {
  rotulo: string
  chave: string
  grupo: string
  secreto: boolean
  configurada: boolean
  valor: string
}

export function listarIntegracoes() {
  return req<{ integracoes: Integracao[] }>('/config')
}
