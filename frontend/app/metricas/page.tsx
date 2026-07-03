'use client'

const CARDS = [
  { rotulo: 'Swipe rate', hint: '% que passa do slide 1' },
  { rotulo: 'Saves', hint: 'salvamentos por post' },
  { rotulo: 'Shares', hint: 'compartilhamentos' },
  { rotulo: 'Completion', hint: '% que chega ao slide 8' },
]

export default function MetricasPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Métricas
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Desempenho dos posts publicados.
        </p>
      </div>

      <div className="rounded-xl border border-electric/30 bg-electric/5 px-5 py-4 font-body text-sm text-neutral-300">
        <span className="font-display font-semibold text-electric">
          Conecte a Instagram Graph API
        </span>{' '}
        para ver métricas. Os cards abaixo mostram o que será acompanhado.
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((c) => (
          <div key={c.rotulo} className="card p-5">
            <p className="font-display text-xs uppercase tracking-wider text-neutral-500">
              {c.rotulo}
            </p>
            <p className="mt-3 font-display text-4xl font-bold text-neutral-700">—</p>
            <p className="mt-2 font-body text-xs text-neutral-600">{c.hint}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
