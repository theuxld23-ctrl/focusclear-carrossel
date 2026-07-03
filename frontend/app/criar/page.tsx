'use client'

import { useEffect, useState } from 'react'
import { criarJob, getJob, type JobStatus } from '@/lib/api'
import StatusBadge from '@/components/StatusBadge'
import { tempoDecorrido } from '@/lib/format'

const PILARES = [
  { value: 'futebol', label: 'Futebol', ativo: true },
  { value: 'cultura_pop', label: 'Cultura Pop / Fofoca', ativo: false },
  { value: 'musica_popular', label: 'Música Popular', ativo: false },
  { value: 'datas_sazonais', label: 'Datas e Sazonais', ativo: false },
]
const FORMATOS = ['carrossel', 'reel', 'motion']
const TURNOS = [
  { value: 'manha', label: 'Manhã — jogos de ontem' },
  { value: 'tarde', label: 'Tarde — momentos históricos' },
]

type Tracked = { id: string; status: JobStatus; erro_msg: string | null; desde: string }

function isTerminal(s: JobStatus) {
  return s === 'concluido' || s === 'erro'
}

export default function CriarPage() {
  const [tema, setTema] = useState('')
  const [pilar, setPilar] = useState('futebol')
  const [formato, setFormato] = useState('carrossel')
  const [turno, setTurno] = useState('manha')

  const [enviando, setEnviando] = useState(false)
  const [erroSubmit, setErroSubmit] = useState<string | null>(null)
  const [tracked, setTracked] = useState<Tracked | null>(null)
  const [tick, setTick] = useState(0) // força re-render do tempo decorrido

  // Pré-preenche a partir de ?tema=&pilar= (ex.: "criar a partir disso" em /tendencias).
  // Aditivo: só roda no mount e não muda nada quando não há query string.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
    const t = q.get('tema')
    const p = q.get('pilar')
    if (t) setTema(t)
    if (p) setPilar(p)
  }, [])

  // Polling do job a cada 2s até concluir ou dar erro.
  useEffect(() => {
    if (!tracked || isTerminal(tracked.status)) return
    const t = setTimeout(async () => {
      try {
        const j = await getJob(tracked.id)
        setTracked((prev) =>
          prev && prev.id === j.id
            ? { ...prev, status: j.status, erro_msg: j.erro_msg }
            : prev,
        )
      } catch (e) {
        setTracked((prev) =>
          prev ? { ...prev, status: 'erro', erro_msg: `falha no polling: ${(e as Error).message}` } : prev,
        )
      }
    }, 2000)
    return () => clearTimeout(t)
  }, [tracked])

  // Relógio para o "há Xs" enquanto roda.
  useEffect(() => {
    if (!tracked || isTerminal(tracked.status)) return
    const i = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(i)
  }, [tracked])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setErroSubmit(null)
    setTracked(null)
    try {
      const { job_id, status } = await criarJob({
        pilar,
        formato,
        turno,
        tema: tema.trim() || null,
      })
      setTracked({ id: job_id, status, erro_msg: null, desde: new Date().toISOString() })
    } catch (e) {
      setErroSubmit((e as Error).message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Criar conteúdo
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Dispara o motor e acompanha o status do job em tempo real.
        </p>
      </div>

      <form onSubmit={onSubmit} className="card space-y-5 p-6">
        <div>
          <label className="label" htmlFor="tema">
            Tema <span className="text-neutral-600">(opcional)</span>
          </label>
          <input
            id="tema"
            className="input"
            placeholder="ex.: a virada emocional da estreia do Brasil"
            value={tema}
            onChange={(e) => setTema(e.target.value)}
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="pilar">Pilar</label>
            <select
              id="pilar"
              className="input"
              value={pilar}
              onChange={(e) => setPilar(e.target.value)}
            >
              {PILARES.map((p) => (
                <option key={p.value} value={p.value} disabled={!p.ativo}>
                  {p.label}
                  {p.ativo ? '' : ' — em breve'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="formato">Formato</label>
            <select
              id="formato"
              className="input"
              value={formato}
              onChange={(e) => setFormato(e.target.value)}
            >
              {FORMATOS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="turno">Turno</label>
            <select
              id="turno"
              className="input"
              value={turno}
              onChange={(e) => setTurno(e.target.value)}
            >
              {TURNOS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={enviando}
            className="rounded-lg bg-electric px-5 py-2.5 font-display text-sm font-semibold text-white transition-colors hover:bg-electric-soft disabled:cursor-not-allowed disabled:opacity-50"
          >
            {enviando ? 'Enviando…' : 'Disparar job'}
          </button>
          {erroSubmit && (
            <span className="font-body text-sm text-red-400">{erroSubmit}</span>
          )}
        </div>
      </form>

      {tracked && (
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <StatusBadge status={tracked.status} />
              {!isTerminal(tracked.status) && (
                <span className="font-body text-xs text-neutral-500">
                  há {tempoDecorrido(tracked.desde)}
                  <span className="sr-only">{tick}</span>
                </span>
              )}
            </div>
            {isTerminal(tracked.status) && (
              <button
                onClick={() => setTracked(null)}
                className="font-display text-xs font-medium text-neutral-400 hover:text-neutral-200"
              >
                Novo job
              </button>
            )}
          </div>

          <div className="mt-4 space-y-1 font-body text-sm">
            <p className="text-neutral-400">
              Job <span className="font-mono text-neutral-200">{tracked.id}</span>
            </p>
            {tracked.status === 'rodando' && (
              <p className="text-neutral-500">O motor está pesquisando…</p>
            )}
            {tracked.status === 'concluido' && (
              <p className="text-emerald-400">
                Concluído. Veja o resultado na aba Biblioteca.
              </p>
            )}
            {tracked.status === 'erro' && tracked.erro_msg && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-red-300">
                {tracked.erro_msg}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
