'use client'

import { useCallback, useEffect, useState } from 'react'
import { listarJobs, type Job } from '@/lib/api'
import StatusBadge from '@/components/StatusBadge'
import { tempoDecorrido } from '@/lib/format'

export default function FilaPage() {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    try {
      setJobs(await listarJobs())
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
    const i = setInterval(carregar, 3000) // atualiza a fila a cada 3s
    return () => clearInterval(i)
  }, [carregar])

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
            Fila
          </h1>
          <p className="mt-1 font-body text-sm text-neutral-500">
            Jobs recentes — atualiza automaticamente a cada 3s.
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

      {jobs === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : jobs.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="font-body text-sm text-neutral-500">
            Fila vazia. Dispare um job na aba{' '}
            <span className="text-electric">Criar</span>.
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-carbon-600 overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-5 py-3 font-display text-xs uppercase tracking-wider text-neutral-500">
            <span>Job</span>
            <span className="text-right">Formato</span>
            <span className="text-right">Status</span>
            <span className="text-right">Há</span>
          </div>
          {jobs.map((job) => (
            <div
              key={job.id}
              className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-5 py-3.5 transition-colors hover:bg-carbon-800/60"
            >
              <div className="min-w-0">
                <p className="truncate font-body text-sm text-neutral-200">
                  {job.tema || <span className="text-neutral-500">sem tema</span>}
                </p>
                <p className="font-body text-xs text-neutral-600">
                  {job.pilar}
                  {job.turno ? ` · ${job.turno}` : ''} ·{' '}
                  <span className="font-mono">{job.id.slice(0, 8)}</span>
                </p>
              </div>
              <span className="text-right font-body text-xs text-neutral-400">
                {job.formato}
              </span>
              <span className="text-right">
                <StatusBadge status={job.status} />
              </span>
              <span className="text-right font-body text-xs tabular-nums text-neutral-500">
                {tempoDecorrido(job.criado_em)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
