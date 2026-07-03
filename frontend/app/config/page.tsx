'use client'

import { useCallback, useEffect, useState } from 'react'
import { listarIntegracoes, type Integracao } from '@/lib/api'

export default function ConfigPage() {
  const [itens, setItens] = useState<Integracao[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    try {
      const r = await listarIntegracoes()
      setItens(r.integracoes)
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const grupos = agrupar(itens ?? [])
  const configuradas = (itens ?? []).filter((i) => i.configurada).length
  const total = itens?.length ?? 0

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Config
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Status das integrações do <code className="text-neutral-400">.env</code>. Só leitura —
          edite as chaves no arquivo, não pela UI.
        </p>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {itens === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : (
        <>
          <div className="card flex items-center justify-between px-5 py-4">
            <span className="font-body text-sm text-neutral-400">
              workspace: <span className="text-neutral-200">focusclear</span>
            </span>
            <span className="font-display text-sm font-medium text-neutral-300">
              {configuradas}/{total} configuradas
            </span>
          </div>

          {Object.entries(grupos).map(([grupo, lista]) => (
            <div key={grupo} className="space-y-3">
              <h2 className="font-display text-xs font-semibold uppercase tracking-wider text-neutral-500">
                {grupo}
              </h2>
              <div className="card divide-y divide-carbon-600 overflow-hidden">
                {lista.map((i) => (
                  <div key={i.chave} className="flex items-center gap-4 px-5 py-3.5">
                    <div className="min-w-0 flex-1">
                      <p className="font-body text-sm text-neutral-200">{i.rotulo}</p>
                      <p className="font-mono text-xs text-neutral-600">{i.chave}</p>
                    </div>
                    <input
                      readOnly
                      value={i.configurada ? i.valor : '—'}
                      className="w-40 rounded-lg border border-carbon-600 bg-carbon-900 px-3 py-1.5 text-right font-mono text-xs text-neutral-400"
                    />
                    <span
                      className={`w-24 shrink-0 text-right font-display text-xs font-medium ${
                        i.configurada ? 'text-emerald-400' : 'text-amber-400/80'
                      }`}
                    >
                      {i.configurada ? 'configurada' : 'pendente'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

function agrupar(itens: Integracao[]): Record<string, Integracao[]> {
  const out: Record<string, Integracao[]> = {}
  for (const i of itens) {
    ;(out[i.grupo] ??= []).push(i)
  }
  return out
}
