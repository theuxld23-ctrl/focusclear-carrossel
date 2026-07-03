'use client'

import { useState } from 'react'
import { imagemAssetUrl } from '@/lib/api'

// Export por asset. v1: o download é o arquivo nativo — a diferença entre
// plataformas é só a label/nome do arquivo (a estrutura fica pronta pra ajustes
// de formato por plataforma: thumbnail, duração máxima). Instagram/TikTok/Shorts
// usam a mesma resolução hoje (carrossel 4:5, reel/motion 9:16).
const PLATAFORMAS = [
  { chave: 'instagram', label: 'Baixar para Instagram' },
  { chave: 'tiktok', label: 'Baixar para TikTok' },
  { chave: 'shorts', label: 'Baixar para YouTube Shorts' },
]

export default function ExportMenu({
  assetId,
  ext,
  base,
}: {
  assetId: string
  ext: string // 'png' | 'webm' | 'mp4' ...
  base: string // nome-base sugerido (ex.: 'espanha-cabo-verde')
}) {
  const [aberto, setAberto] = useState(false)
  const href = imagemAssetUrl(assetId)

  return (
    <div className="relative">
      <button
        onClick={() => setAberto((v) => !v)}
        className="w-full rounded-lg border border-carbon-600 px-3 py-2 font-display text-xs font-medium text-neutral-300 transition-colors hover:bg-carbon-700"
      >
        Exportar {aberto ? '▴' : '▾'}
      </button>
      {aberto && (
        <div className="absolute bottom-full left-0 z-20 mb-2 w-full overflow-hidden rounded-lg border border-carbon-600 bg-carbon-900 shadow-xl">
          {PLATAFORMAS.map((p) => (
            <a
              key={p.chave}
              href={href}
              download={`focusclear-${p.chave}-${base}.${ext}`}
              onClick={() => setAberto(false)}
              className="block px-3.5 py-2.5 font-body text-xs text-neutral-300 transition-colors hover:bg-electric/15 hover:text-electric"
            >
              {p.label}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
