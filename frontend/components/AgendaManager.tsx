'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  listarAgenda,
  criarAgenda,
  atualizarAgenda,
  removerAgenda,
  listarPilares,
  type Agenda,
  type Pilar,
} from '@/lib/api'

const FORMATOS = ['carrossel', 'reel', 'motion']
const TURNOS = [
  { valor: '', rotulo: '—' },
  { valor: 'manha', rotulo: 'manhã' },
  { valor: 'tarde', rotulo: 'tarde' },
]

// Cron → descrição legível simples (só HH:MM diário; senão mostra o cron cru).
function descreveCron(cron: string): string {
  const p = cron.trim().split(/\s+/)
  if (p.length === 5 && p[2] === '*' && p[3] === '*' && p[4] === '*') {
    const [m, h] = p
    if (/^\d+$/.test(m) && /^\d+$/.test(h)) {
      return `todo dia ${h.padStart(2, '0')}:${m.padStart(2, '0')}`
    }
  }
  return cron
}

export default function AgendaManager() {
  const [linhas, setLinhas] = useState<Agenda[] | null>(null)
  const [pilares, setPilares] = useState<Pilar[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [pilar, setPilar] = useState('futebol')
  const [formato, setFormato] = useState('carrossel')
  const [turno, setTurno] = useState('')
  const [cron, setCron] = useState('0 6 * * *')
  const [salvando, setSalvando] = useState(false)

  const carregar = useCallback(async () => {
    try {
      const [ags, pils] = await Promise.all([listarAgenda(), listarPilares()])
      setLinhas(ags)
      setPilares(pils)
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const adicionar = async () => {
    setSalvando(true)
    try {
      await criarAgenda({
        pilar,
        formato,
        turno: turno || null,
        horario_cron: cron,
      })
      await carregar()
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    } finally {
      setSalvando(false)
    }
  }

  const alternarAtivo = async (a: Agenda) => {
    try {
      await atualizarAgenda(a.id, { ativo: !a.ativo })
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  const excluir = async (a: Agenda) => {
    try {
      await removerAgenda(a.id)
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  const opcoesPilar = pilares.length
    ? pilares.map((p) => (p.config?.chave as string) || p.nome)
    : ['futebol', 'cultura_pop', 'musica_popular', 'datas_sazonais']

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-lg font-bold tracking-tight text-neutral-100">
            Agendamentos
          </h2>
          <p className="mt-1 font-body text-sm text-neutral-500">
            O scheduler lê estas linhas e cria os jobs nos horários (cron). Sem
            nenhuma linha ativa, cai no padrão 06h/13h.
          </p>
        </div>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      {/* Form de novo agendamento */}
      <div className="card grid grid-cols-1 gap-3 p-4 sm:grid-cols-[1fr_1fr_1fr_1fr_auto]">
        <label className="flex flex-col gap-1">
          <span className="font-display text-xs uppercase tracking-wider text-neutral-500">
            Pilar
          </span>
          <select
            value={pilar}
            onChange={(e) => setPilar(e.target.value)}
            className="rounded-lg border border-carbon-600 bg-carbon-800 px-3 py-2 font-body text-sm text-neutral-200"
          >
            {opcoesPilar.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-display text-xs uppercase tracking-wider text-neutral-500">
            Formato
          </span>
          <select
            value={formato}
            onChange={(e) => setFormato(e.target.value)}
            className="rounded-lg border border-carbon-600 bg-carbon-800 px-3 py-2 font-body text-sm text-neutral-200"
          >
            {FORMATOS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-display text-xs uppercase tracking-wider text-neutral-500">
            Turno
          </span>
          <select
            value={turno}
            onChange={(e) => setTurno(e.target.value)}
            className="rounded-lg border border-carbon-600 bg-carbon-800 px-3 py-2 font-body text-sm text-neutral-200"
          >
            {TURNOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-display text-xs uppercase tracking-wider text-neutral-500">
            Cron
          </span>
          <input
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            placeholder="0 6 * * *"
            className="rounded-lg border border-carbon-600 bg-carbon-800 px-3 py-2 font-mono text-sm text-neutral-200"
          />
        </label>
        <div className="flex items-end">
          <button
            onClick={adicionar}
            disabled={salvando || !cron.trim()}
            className="w-full rounded-lg bg-electric px-4 py-2 font-display text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40 sm:w-auto"
          >
            {salvando ? 'Salvando…' : 'Adicionar'}
          </button>
        </div>
      </div>

      {/* Lista */}
      {linhas === null ? (
        <p className="font-body text-sm text-neutral-500">Carregando…</p>
      ) : linhas.length === 0 ? (
        <div className="card p-6 text-center">
          <p className="font-body text-sm text-neutral-500">
            Nenhum agendamento — o scheduler usa o padrão 06h/13h (retrocompat).
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-carbon-600 overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-5 py-3 font-display text-xs uppercase tracking-wider text-neutral-500">
            <span>Agendamento</span>
            <span className="text-right">Turno</span>
            <span className="text-right">Quando</span>
            <span className="text-right">Ativo</span>
            <span className="text-right">Ação</span>
          </div>
          {linhas.map((a) => (
            <div
              key={a.id}
              className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-4 px-5 py-3.5 transition-colors hover:bg-carbon-800/60"
            >
              <div className="min-w-0">
                <p className="truncate font-body text-sm text-neutral-200">
                  {a.pilar} · {a.formato}
                </p>
                <p className="font-mono text-xs text-neutral-600">{a.horario_cron}</p>
              </div>
              <span className="text-right font-body text-xs text-neutral-400">
                {a.turno || '—'}
              </span>
              <span className="text-right font-body text-xs text-neutral-400">
                {descreveCron(a.horario_cron)}
              </span>
              <span className="text-right">
                <button
                  onClick={() => alternarAtivo(a)}
                  className={`rounded-full border px-2.5 py-0.5 font-display text-xs font-medium ${
                    a.ativo
                      ? 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
                      : 'border-neutral-500/30 bg-neutral-500/15 text-neutral-400'
                  }`}
                >
                  {a.ativo ? 'ativo' : 'pausado'}
                </button>
              </span>
              <span className="text-right">
                <button
                  onClick={() => excluir(a)}
                  className="rounded-lg border border-carbon-600 px-2.5 py-1 font-display text-xs text-neutral-400 transition-colors hover:border-red-500/40 hover:text-red-300"
                >
                  excluir
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
