'use client'

import { imagemAssetUrl } from '@/lib/api'

// Reel: se o arquivo é vídeo (mp4/webm), mostra player; senão, poster placeholder.
export default function ReelPreview({
  id,
  caminho,
}: {
  id: string
  caminho: string | null
}) {
  const ehVideo = !!caminho && /\.(mp4|webm)$/i.test(caminho)
  const src = imagemAssetUrl(id)

  return (
    <div className="relative aspect-[9/16] overflow-hidden border-b border-carbon-600 bg-carbon-900">
      {ehVideo ? (
        <video
          src={src}
          className="h-full w-full object-cover"
          controls
          loop
          muted
          playsInline
          preload="metadata"
        />
      ) : (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt="poster do reel" className="h-full w-full object-cover" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-electric/90 text-2xl text-carbon-900">
              ▶
            </span>
          </div>
        </>
      )}
      <span className="pointer-events-none absolute bottom-2.5 left-1/2 -translate-x-1/2 rounded-full bg-carbon-900/75 px-2.5 py-0.5 font-body text-[10px] text-neutral-300 backdrop-blur-sm">
        conteúdo gerado por IA
      </span>
    </div>
  )
}
