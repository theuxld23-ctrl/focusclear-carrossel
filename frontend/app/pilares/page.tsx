'use client'

import { useCallback, useEffect, useState } from 'react'
import { listarPilares, atualizarPilar, type Pilar } from '@/lib/api'

const STATUS = ['ativo', 'planejado', 'desativado'] as const

const CORES: Record<string, string> = {
  ativo: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  planejado: 'bg-electric/15 text-electric border-electric/40',
  desativado: 'bg-neutral-500/15 text-neutral-400 border-neutral-500/30',
}

export default function PilaresPage() {
  const [pilares, setPilares] = useState<Pilar[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [editando, setEditando] = useState<number | null>(null)
  const [rascunho, setRascunho] = useState('')

  const carregar = useCallback(async () => {
    try {
      setPilares(await listarPilares())
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  function aplicar(id: number, patch: Partial<Pilar>) {
    setPilares((prev) => (prev ? prev.map((p) => (p.id === id ? { ...p, ...patch } : p)) : prev))
  }

  async function mudarStatus(p: Pilar, status: string) {
    aplicar(p.id, { status })
    try {
      await atualizarPilar(p.id, { status })
    } catch (e) {
      setErro((e as Error).message)
      carregar()
    }
  }

  function abrirEdicao(p: Pilar) {
    setEditando(p.id)
    setRascunho(JSON.stringify(p.config, null, 2))
  }

  async function salvarConfig(p: Pilar) {
    let config: Record<string, unknown>
    try {
      config = JSON.parse(rascunho)
    } catch {
      setErro('Config inválido — JSON malformado')
      return
    }
    try {
      const atualizado = await atualizarPilar(p.id, { config })
      aplicar(p.id, { config: atualizado.config })
      setEditando(null)
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Pilares
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Ative, desative e edite a config de cada pilar de conteúdo.
        </p>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {pilares === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : (
        <div className="space-y-4">
          {pilares.map((p) => {
            const cfg = p.config || {}
            return (
              <div key={p.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="font-display text-lg font-semibold text-neutral-50">
                        {p.nome}
                      </h2>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 font-display text-xs font-medium ${CORES[p.status] || CORES.desativado}`}
                      >
                        {p.status}
                      </span>
                      {typeof cfg.prioridade === 'number' && (
                        <span className="font-body text-xs text-neutral-600">
                          prioridade {cfg.prioridade as number}
                        </span>
                      )}
                    </div>
                    {typeof cfg.descricao === 'string' && cfg.descricao && (
                      <p className="mt-1.5 max-w-2xl font-body text-sm text-neutral-500">
                        {cfg.descricao as string}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      value={p.status}
                      onChange={(e) => mudarStatus(p, e.target.value)}
                      className="input w-auto py-1.5 text-sm"
                      aria-label={`status de ${p.nome}`}
                    >
                      {STATUS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => (editando === p.id ? setEditando(null) : abrirEdicao(p))}
                      className="rounded-lg border border-carbon-600 px-3 py-1.5 font-display text-xs font-medium text-neutral-300 transition-colors hover:bg-carbon-700"
                    >
                      {editando === p.id ? 'Fechar' : 'Editar config'}
                    </button>
                  </div>
                </div>

                {editando === p.id && (
                  <div className="mt-4 space-y-3">
                    <textarea
                      value={rascunho}
                      onChange={(e) => setRascunho(e.target.value)}
                      spellCheck={false}
                      className="input h-56 font-mono text-xs leading-relaxed"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => salvarConfig(p)}
                        className="rounded-lg bg-electric px-4 py-2 font-display text-sm font-semibold text-white transition-colors hover:bg-electric-soft"
                      >
                        Salvar config
                      </button>
                      <button
                        onClick={() => setEditando(null)}
                        className="rounded-lg border border-carbon-600 px-4 py-2 font-display text-sm font-medium text-neutral-300 hover:bg-carbon-700"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
