'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  atualizarStatusAsset,
  listarAssets,
  type Asset,
  type AssetStatus,
} from '@/lib/api'
import StatusBadge from '@/components/StatusBadge'
import CarrosselPreview, { type SlidePreview } from '@/components/CarrosselPreview'
import ReelPreview from '@/components/ReelPreview'
import { dataHora } from '@/lib/format'

// Fluxo de aprovação: cada status avança para o próximo com o mesmo PATCH.
const PROXIMO: Partial<Record<AssetStatus, { proximo: AssetStatus; label: string }>> = {
  rascunho: { proximo: 'aprovado', label: 'Aprovar' },
  aprovado: { proximo: 'agendado', label: 'Agendar' },
  agendado: { proximo: 'publicado', label: 'Publicar' },
}

// Um carrossel/motion = os slides que compartilham a mesma pasta (engine/output/<dir>/).
interface Carrossel {
  key: string
  tipo: 'carrossel' | 'motion'
  assets: Asset[]
  slides: SlidePreview[]
  status: AssetStatus
  perfil: string
  times: string[]
  fase: string
  criado_em: string
}

const asStr = (v: unknown) => (typeof v === 'string' ? v : '')
const asN = (v: unknown) => (typeof v === 'number' ? v : Number(v) || 0)
const dirDe = (caminho: string) => caminho.replace(/\/[^/]*$/, '')

// Agrupa assets de slides (tipo "slide" ou "motion") por pasta em cards navegáveis.
function agruparSlides(assets: Asset[], tipo: 'carrossel' | 'motion'): Carrossel[] {
  const mapa = new Map<string, Asset[]>()
  for (const a of assets) {
    const k = dirDe(a.caminho as string)
    if (!mapa.has(k)) mapa.set(k, [])
    mapa.get(k)!.push(a)
  }
  const grupos = [...mapa.entries()].map(([key, grupo]) => {
    const ordenados = [...grupo].sort((x, y) => asN(x.metadados.n) - asN(y.metadados.n))
    const capa = ordenados.find((a) => asN(a.metadados.n) === 1) ?? ordenados[0]
    const times = capa.metadados.times
    return {
      key,
      tipo,
      assets: ordenados,
      slides: ordenados.map((a) => ({
        id: a.id,
        n: asN(a.metadados.n),
        funcao: asStr(a.metadados.funcao),
        caminho: a.caminho,
      })),
      status: capa.status,
      perfil: asStr(capa.metadados.perfil),
      times: Array.isArray(times) ? (times as string[]) : [],
      fase: asStr(capa.metadados.fase_copa),
      criado_em: capa.criado_em,
    }
  })
  grupos.sort((a, b) => b.criado_em.localeCompare(a.criado_em))
  return grupos
}

function agrupar(assets: Asset[]): {
  carrosseis: Carrossel[]
  motions: Carrossel[]
  reels: Asset[]
  legado: Asset[]
} {
  const carrosseis = agruparSlides(
    assets.filter((a) => a.tipo === 'slide' && a.caminho),
    'carrossel',
  )
  const motions = agruparSlides(
    assets.filter((a) => a.tipo === 'motion' && a.caminho),
    'motion',
  )
  const reels = assets
    .filter((a) => a.tipo === 'reel' && a.caminho)
    .sort((a, b) => b.criado_em.localeCompare(a.criado_em))
  const legado = assets.filter(
    (a) => !(['slide', 'motion', 'reel'].includes(a.tipo) && a.caminho),
  )
  return { carrosseis, motions, reels, legado }
}

export default function BibliotecaPage() {
  const [assets, setAssets] = useState<Asset[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [atualizando, setAtualizando] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    try {
      setAssets(await listarAssets())
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const { carrosseis, motions, reels, legado } = useMemo(
    () => agrupar(assets ?? []),
    [assets],
  )

  // Avança o status do carrossel inteiro (PATCH em todos os slides).
  async function avancarCarrossel(c: Carrossel) {
    const passo = PROXIMO[c.status]
    if (!passo) return
    setAtualizando(c.key)
    try {
      await Promise.all(c.assets.map((a) => atualizarStatusAsset(a.id, passo.proximo)))
      const ids = new Set(c.assets.map((a) => a.id))
      setAssets((prev) =>
        prev ? prev.map((a) => (ids.has(a.id) ? { ...a, status: passo.proximo } : a)) : prev,
      )
    } catch (e) {
      setErro((e as Error).message)
    } finally {
      setAtualizando(null)
    }
  }

  // Avança o status de um único asset (reel).
  async function avancarAsset(a: Asset) {
    const passo = PROXIMO[a.status]
    if (!passo) return
    setAtualizando(a.id)
    try {
      await atualizarStatusAsset(a.id, passo.proximo)
      setAssets((prev) =>
        prev ? prev.map((x) => (x.id === a.id ? { ...x, status: passo.proximo } : x)) : prev,
      )
    } catch (e) {
      setErro((e as Error).message)
    } finally {
      setAtualizando(null)
    }
  }

  const vazio =
    assets !== null &&
    carrosseis.length === 0 &&
    motions.length === 0 &&
    reels.length === 0 &&
    legado.length === 0

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
            Biblioteca
          </h1>
          <p className="mt-1 font-body text-sm text-neutral-500">
            Carrosséis, motion e reels gerados pelo motor. Navegue, revise e aprove.
          </p>
        </div>
        <button
          onClick={carregar}
          className="rounded-lg border border-carbon-600 px-3 py-1.5 font-display text-xs font-medium text-neutral-300 transition-colors hover:bg-carbon-700"
        >
          Atualizar
        </button>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {assets === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : vazio ? (
        <div className="card p-10 text-center">
          <p className="font-body text-sm text-neutral-500">
            Nenhum carrossel ainda. Crie um job na aba{' '}
            <span className="text-electric">Criar</span>.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {carrosseis.map((c) => {
            const passo = PROXIMO[c.status]
            return (
              <div key={c.key} className="card flex flex-col overflow-hidden">
                <div className="relative">
                  <CarrosselPreview slides={c.slides} />
                  <span className="pointer-events-none absolute left-2.5 top-2.5">
                    <StatusBadge status={c.status} />
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-3 p-4">
                  <div className="space-y-1 font-body text-xs text-neutral-500">
                    {c.times.length === 2 && (
                      <p className="text-neutral-300">
                        {c.times[0]} <span className="text-neutral-600">x</span> {c.times[1]}
                      </p>
                    )}
                    <p>
                      {c.perfil && (
                        <span className="text-electric">{c.perfil}</span>
                      )}
                      {c.fase && <span className="text-neutral-600"> · {c.fase}</span>}
                      <span className="text-neutral-600"> · {c.slides.length} slides</span>
                    </p>
                    <p>{dataHora(c.criado_em)}</p>
                  </div>

                  <div className="mt-auto">
                    {passo ? (
                      <button
                        onClick={() => avancarCarrossel(c)}
                        disabled={atualizando === c.key}
                        className="w-full rounded-lg bg-electric/15 px-3 py-2 font-display text-sm font-semibold text-electric transition-colors hover:bg-electric/25 disabled:opacity-50"
                      >
                        {atualizando === c.key ? '…' : passo.label}
                      </button>
                    ) : (
                      <p className="text-center font-body text-xs text-neutral-600">
                        publicado ✓
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Motion — carrossel com 1-2 slides animados (webm); navegável + badge */}
          {motions.map((c) => {
            const passo = PROXIMO[c.status]
            const nAnimados = c.slides.filter(
              (s) => !!s.caminho && /\.(mp4|webm)$/i.test(s.caminho),
            ).length
            return (
              <div key={c.key} className="card flex flex-col overflow-hidden">
                <div className="relative">
                  <CarrosselPreview slides={c.slides} />
                  <span className="pointer-events-none absolute left-2.5 top-2.5">
                    <StatusBadge status={c.status} />
                  </span>
                  <span className="pointer-events-none absolute right-2.5 top-2.5 rounded-full bg-carbon-900/75 px-2 py-0.5 font-display text-[10px] uppercase tracking-wider text-electric backdrop-blur-sm">
                    motion
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-3 p-4">
                  <div className="space-y-1 font-body text-xs text-neutral-500">
                    {c.times.length === 2 && (
                      <p className="text-neutral-300">
                        {c.times[0]} <span className="text-neutral-600">x</span> {c.times[1]}
                      </p>
                    )}
                    <p>
                      {c.perfil && <span className="text-electric">{c.perfil}</span>}
                      {c.fase && <span className="text-neutral-600"> · {c.fase}</span>}
                      <span className="text-neutral-600"> · {c.slides.length} slides</span>
                      {nAnimados > 0 && (
                        <span className="text-neutral-600"> · {nAnimados} animados</span>
                      )}
                    </p>
                    <p>{dataHora(c.criado_em)}</p>
                  </div>

                  <div className="mt-auto">
                    {passo ? (
                      <button
                        onClick={() => avancarCarrossel(c)}
                        disabled={atualizando === c.key}
                        className="w-full rounded-lg bg-electric/15 px-3 py-2 font-display text-sm font-semibold text-electric transition-colors hover:bg-electric/25 disabled:opacity-50"
                      >
                        {atualizando === c.key ? '…' : passo.label}
                      </button>
                    ) : (
                      <p className="text-center font-body text-xs text-neutral-600">
                        publicado ✓
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Reels — player de vídeo (webm/mp4) ou poster placeholder */}
          {reels.map((r) => {
            const passo = PROXIMO[r.status]
            const times = Array.isArray(r.metadados.times) ? (r.metadados.times as string[]) : []
            const placeholder = r.metadados.placeholder === true
            return (
              <div key={r.id} className="card flex flex-col overflow-hidden">
                <div className="relative">
                  <ReelPreview id={r.id} caminho={r.caminho} />
                  <span className="pointer-events-none absolute left-2.5 top-2.5">
                    <StatusBadge status={r.status} />
                  </span>
                  <span className="pointer-events-none absolute right-2.5 top-2.5 rounded-full bg-carbon-900/75 px-2 py-0.5 font-display text-[10px] uppercase tracking-wider text-electric backdrop-blur-sm">
                    reel
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-3 p-4">
                  <div className="space-y-1 font-body text-xs text-neutral-500">
                    {times.length === 2 && (
                      <p className="text-neutral-300">
                        {times[0]} <span className="text-neutral-600">x</span> {times[1]}
                      </p>
                    )}
                    <p>
                      {asStr(r.metadados.perfil) && (
                        <span className="text-electric">{asStr(r.metadados.perfil)}</span>
                      )}
                      {typeof r.metadados.duracao_estimada_s === 'number' && (
                        <span className="text-neutral-600"> · ~{r.metadados.duracao_estimada_s}s</span>
                      )}
                      {placeholder && <span className="text-amber-400/80"> · placeholder</span>}
                    </p>
                    <p>{dataHora(r.criado_em)}</p>
                  </div>

                  <div className="mt-auto">
                    {passo ? (
                      <button
                        onClick={() => avancarAsset(r)}
                        disabled={atualizando === r.id}
                        className="w-full rounded-lg bg-electric/15 px-3 py-2 font-display text-sm font-semibold text-electric transition-colors hover:bg-electric/25 disabled:opacity-50"
                      >
                        {atualizando === r.id ? '…' : passo.label}
                      </button>
                    ) : (
                      <p className="text-center font-body text-xs text-neutral-600">publicado ✓</p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Assets legados sem PNG (fases anteriores) — placeholder simples */}
          {legado.map((a) => (
            <div key={a.id} className="card flex flex-col overflow-hidden opacity-70">
              <div className="relative flex aspect-[4/5] items-center justify-center border-b border-carbon-600 bg-gradient-to-br from-carbon-700 to-carbon-900">
                <span className="font-display text-xs uppercase tracking-widest text-neutral-600">
                  {a.tipo}
                </span>
                <span className="absolute right-2.5 top-2.5">
                  <StatusBadge status={a.status} />
                </span>
              </div>
              <div className="p-4 font-body text-xs text-neutral-500">
                <p>sem PNG (fase anterior)</p>
                <p>{dataHora(a.criado_em)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
