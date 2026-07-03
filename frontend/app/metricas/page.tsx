'use client'

import { useEffect, useState } from 'react'
import { listarMetricas, type MetricasResposta } from '@/lib/api'

const CARDS: {
  chave: 'swipe_rate' | 'saves' | 'shares' | 'completion'
  rotulo: string
  hint: string
  sufixo?: string
}[] = [
  { chave: 'swipe_rate', rotulo: 'Swipe rate', hint: '% que passa do slide 1', sufixo: '%' },
  { chave: 'saves', rotulo: 'Saves', hint: 'salvamentos por post' },
  { chave: 'shares', rotulo: 'Shares', hint: 'compartilhamentos' },
  { chave: 'completion', rotulo: 'Completion', hint: '% que chega ao slide 8', sufixo: '%' },
]

export default function MetricasPage() {
  const [dados, setDados] = useState<MetricasResposta | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    listarMetricas()
      .then((d) => {
        setDados(d)
        setErro(null)
      })
      .catch((e) => setErro((e as Error).message))
  }, [])

  const resumo = dados?.resumo ?? null
  const temDados = !!resumo && resumo.n_posts > 0

  const valorCard = (chave: (typeof CARDS)[number]['chave'], sufixo?: string) => {
    if (!resumo) return '—'
    const v = resumo[chave]
    if (v === null || v === undefined) return '—'
    return `${v}${sufixo ?? ''}`
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Métricas
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Desempenho dos posts publicados
          {temDados ? ` · ${resumo!.n_posts} posts` : ''}.
        </p>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {!temDados && (
        <div className="rounded-xl border border-electric/30 bg-electric/5 px-5 py-4 font-body text-sm text-neutral-300">
          <span className="font-display font-semibold text-electric">
            Sem dados ainda
          </span>{' '}
          — as métricas aparecem quando a Instagram Graph API for conectada{' '}
          <span className="text-neutral-500">(v2)</span>. A estrutura já está pronta
          para recebê-las; os cards abaixo mostram o que será acompanhado.
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((c) => (
          <div key={c.chave} className="card p-5">
            <p className="font-display text-xs uppercase tracking-wider text-neutral-500">
              {c.rotulo}
            </p>
            <p
              className={`mt-3 font-display text-4xl font-bold ${
                temDados ? 'text-neutral-50' : 'text-neutral-700'
              }`}
            >
              {valorCard(c.chave, c.sufixo)}
            </p>
            <p className="mt-2 font-body text-xs text-neutral-600">{c.hint}</p>
          </div>
        ))}
      </div>

      {temDados && dados && (
        <div className="card divide-y divide-carbon-600 overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-5 py-3 font-display text-xs uppercase tracking-wider text-neutral-500">
            <span>Post</span>
            <span className="text-right">Swipe</span>
            <span className="text-right">Saves</span>
            <span className="text-right">Shares</span>
            <span className="text-right">Compl.</span>
          </div>
          {dados.metricas.map((m) => (
            <div
              key={m.id}
              className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-4 px-5 py-3 font-body text-sm text-neutral-200"
            >
              <span className="truncate text-neutral-400">
                {m.asset_id ? m.asset_id.slice(0, 8) : m.periodo || '—'}
              </span>
              <span className="text-right tabular-nums">
                {m.swipe_rate ?? '—'}
                {m.swipe_rate !== null ? '%' : ''}
              </span>
              <span className="text-right tabular-nums">{m.saves ?? '—'}</span>
              <span className="text-right tabular-nums">{m.shares ?? '—'}</span>
              <span className="text-right tabular-nums">
                {m.completion ?? '—'}
                {m.completion !== null ? '%' : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
