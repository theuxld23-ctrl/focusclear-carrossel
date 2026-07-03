'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { listarTendencias, type Tendencia } from '@/lib/api'
import { dataHora } from '@/lib/format'

export default function TendenciasPage() {
  const [tendencias, setTendencias] = useState<Tendencia[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    try {
      setTendencias(await listarTendencias())
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const vazio = tendencias !== null && tendencias.length === 0

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Tendências
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Termos em alta por pilar. Crie um carrossel direto a partir de um deles.
        </p>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {vazio && (
        <div className="rounded-xl border border-electric/30 bg-electric/5 px-5 py-4 font-body text-sm text-neutral-300">
          <span className="font-display font-semibold text-electric">Conecte a Brave API</span>{' '}
          para popular tendências. A estrutura abaixo mostra como cada card aparecerá.
        </div>
      )}

      {tendencias === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {vazio ? (
            <CardExemplo />
          ) : (
            tendencias.map((t) => (
              <CardTendencia key={t.id} t={t} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

function CardTendencia({ t }: { t: Tendencia }) {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between">
        <span className="rounded-full bg-carbon-700 px-2.5 py-0.5 font-display text-xs uppercase tracking-wider text-neutral-400">
          {t.pilar}
        </span>
        <span className="font-display text-sm font-bold text-electric">{t.score}</span>
      </div>
      <p className="font-display text-lg font-semibold text-neutral-50">{t.termo}</p>
      <p className="font-body text-xs text-neutral-600">{dataHora(t.data)}</p>
      <Link
        href={`/criar?tema=${encodeURIComponent(t.termo)}&pilar=${encodeURIComponent(t.pilar)}`}
        className="mt-auto w-full rounded-lg bg-electric/15 px-3 py-2 text-center font-display text-sm font-semibold text-electric transition-colors hover:bg-electric/25"
      >
        Criar a partir disso
      </Link>
    </div>
  )
}

// Card fantasma que ilustra a estrutura enquanto não há tendências reais.
function CardExemplo() {
  return (
    <div className="card flex flex-col gap-3 p-5 opacity-50">
      <div className="flex items-start justify-between">
        <span className="rounded-full bg-carbon-700 px-2.5 py-0.5 font-display text-xs uppercase tracking-wider text-neutral-500">
          futebol
        </span>
        <span className="font-display text-sm font-bold text-neutral-500">—</span>
      </div>
      <p className="font-display text-lg font-semibold text-neutral-400">exemplo de termo</p>
      <p className="font-body text-xs text-neutral-700">pilar · score · data</p>
      <span className="mt-auto w-full rounded-lg border border-carbon-600 px-3 py-2 text-center font-display text-sm font-medium text-neutral-600">
        Criar a partir disso
      </span>
    </div>
  )
}
