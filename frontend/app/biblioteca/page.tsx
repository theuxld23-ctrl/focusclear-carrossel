'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  atualizarStatusAsset,
  listarAssets,
  type Asset,
  type AssetStatus,
} from '@/lib/api'
import StatusBadge from '@/components/StatusBadge'
import { dataHora } from '@/lib/format'

// Fluxo de aprovação: cada status avança para o próximo com o mesmo PATCH.
const PROXIMO: Partial<Record<AssetStatus, { proximo: AssetStatus; label: string }>> = {
  rascunho: { proximo: 'aprovado', label: 'Aprovar' },
  aprovado: { proximo: 'agendado', label: 'Agendar' },
  agendado: { proximo: 'publicado', label: 'Publicar' },
}

function resumoMetadados(m: Record<string, unknown>) {
  const jogos = Array.isArray(m?.jogos_pesquisados) ? m.jogos_pesquisados.length : 0
  const erros = Array.isArray(m?.erros) ? m.erros.length : 0
  const fase = typeof m?.fase_copa === 'string' ? m.fase_copa : null
  return { jogos, erros, fase }
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

  async function avancar(asset: Asset) {
    const passo = PROXIMO[asset.status]
    if (!passo) return
    setAtualizando(asset.id)
    try {
      await atualizarStatusAsset(asset.id, passo.proximo)
      setAssets((prev) =>
        prev
          ? prev.map((a) =>
              a.id === asset.id ? { ...a, status: passo.proximo } : a,
            )
          : prev,
      )
    } catch (e) {
      setErro((e as Error).message)
    } finally {
      setAtualizando(null)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
            Biblioteca
          </h1>
          <p className="mt-1 font-body text-sm text-neutral-500">
            Assets gerados pelo motor. Revise e avance o status de aprovação.
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
      ) : assets.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="font-body text-sm text-neutral-500">
            Nenhum asset ainda. Crie um job na aba{' '}
            <span className="text-electric">Criar</span>.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {assets.map((asset) => {
            const { jogos, erros, fase } = resumoMetadados(asset.metadados)
            const passo = PROXIMO[asset.status]
            return (
              <div key={asset.id} className="card flex flex-col overflow-hidden">
                {/* Preview placeholder — compositor real vem em fase futura */}
                <div className="relative flex aspect-[4/5] items-center justify-center border-b border-carbon-600 bg-gradient-to-br from-carbon-700 to-carbon-900">
                  <span className="font-display text-xs uppercase tracking-widest text-neutral-600">
                    {asset.tipo}
                  </span>
                  <span className="absolute right-2.5 top-2.5">
                    <StatusBadge status={asset.status} />
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-3 p-4">
                  <div className="space-y-1 font-body text-xs text-neutral-500">
                    {fase && (
                      <p>
                        fase: <span className="text-neutral-300">{fase}</span>
                      </p>
                    )}
                    <p>
                      jogos: <span className="text-neutral-300">{jogos}</span>
                      {erros > 0 && (
                        <span className="ml-2 text-amber-400">{erros} erro(s)</span>
                      )}
                    </p>
                    <p>{dataHora(asset.criado_em)}</p>
                  </div>

                  <div className="mt-auto">
                    {passo ? (
                      <button
                        onClick={() => avancar(asset)}
                        disabled={atualizando === asset.id}
                        className="w-full rounded-lg bg-electric/15 px-3 py-2 font-display text-sm font-semibold text-electric transition-colors hover:bg-electric/25 disabled:opacity-50"
                      >
                        {atualizando === asset.id ? '…' : passo.label}
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
        </div>
      )}
    </div>
  )
}
