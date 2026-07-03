'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const tabs = [
  { href: '/criar', label: 'Criar' },
  { href: '/biblioteca', label: 'Biblioteca' },
  { href: '/fila', label: 'Fila' },
  { href: '/tendencias', label: 'Tendências' },
  { href: '/pilares', label: 'Pilares' },
  { href: '/personagem', label: 'Personagem' },
  { href: '/metricas', label: 'Métricas' },
  { href: '/config', label: 'Config' },
]

export default function Nav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-10 border-b border-carbon-600 bg-carbon-900/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center gap-8 px-6 py-4">
        <Link href="/criar" className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-electric shadow-[0_0_12px_2px_rgba(27,79,255,0.6)]" />
          <span className="font-display text-lg font-bold tracking-tight text-neutral-50">
            Focus<span className="text-electric">Clear</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {tabs.map((tab) => {
            const active =
              pathname === tab.href || pathname.startsWith(tab.href + '/')
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={[
                  'rounded-lg px-3.5 py-1.5 font-display text-sm font-medium transition-colors',
                  active
                    ? 'bg-electric/15 text-electric'
                    : 'text-neutral-400 hover:bg-carbon-700 hover:text-neutral-200',
                ].join(' ')}
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>

        <span className="ml-auto hidden font-body text-xs text-neutral-600 sm:block">
          workspace: focusclear
        </span>
      </div>
    </header>
  )
}
