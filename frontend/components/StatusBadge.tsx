import type { AssetStatus, JobStatus } from '@/lib/api'

type Status = JobStatus | AssetStatus

const MAP: Record<Status, { label: string; cls: string; pulse?: boolean }> = {
  // Jobs
  pendente: { label: 'pendente', cls: 'bg-neutral-500/15 text-neutral-300 border-neutral-500/30' },
  rodando: { label: 'rodando', cls: 'bg-electric/15 text-electric border-electric/40', pulse: true },
  concluido: { label: 'concluído', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  erro: { label: 'erro', cls: 'bg-red-500/15 text-red-300 border-red-500/30' },
  // Assets
  rascunho: { label: 'rascunho', cls: 'bg-neutral-500/15 text-neutral-300 border-neutral-500/30' },
  aprovado: { label: 'aprovado', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  agendado: { label: 'agendado', cls: 'bg-electric/15 text-electric border-electric/40' },
  publicado: { label: 'publicado', cls: 'bg-violet-500/15 text-violet-300 border-violet-500/30' },
}

export default function StatusBadge({ status }: { status: string }) {
  const meta = MAP[status as Status] ?? {
    label: status,
    cls: 'bg-neutral-500/15 text-neutral-300 border-neutral-500/30',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-display text-xs font-medium ${meta.cls}`}
    >
      {meta.pulse && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {meta.label}
    </span>
  )
}
