'use client'

import { useRef, useState } from 'react'
import { imagemAssetUrl } from '@/lib/api'

export interface SlidePreview {
  id: string
  n: number
  funcao?: string
  caminho?: string | null // se for vídeo (motion), renderiza <video>
}

const ehVideo = (c?: string | null) => !!c && /\.(mp4|webm)$/i.test(c)

export default function CarrosselPreview({ slides }: { slides: SlidePreview[] }) {
  const [i, setI] = useState(0)
  const total = slides.length
  const toqueX = useRef<number | null>(null)

  if (total === 0) return null

  const ir = (delta: number) => setI((v) => (v + delta + total) % total)

  function onTouchStart(e: React.TouchEvent) {
    toqueX.current = e.touches[0].clientX
  }
  function onTouchEnd(e: React.TouchEvent) {
    if (toqueX.current === null) return
    const dx = e.changedTouches[0].clientX - toqueX.current
    if (Math.abs(dx) > 40) ir(dx < 0 ? 1 : -1)
    toqueX.current = null
  }

  const slide = slides[i]

  return (
    <div
      className="group relative aspect-[4/5] select-none overflow-hidden border-b border-carbon-600 bg-carbon-900"
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {ehVideo(slide.caminho) ? (
        <video
          key={slide.id}
          src={imagemAssetUrl(slide.id)}
          className="h-full w-full object-cover"
          autoPlay
          loop
          muted
          playsInline
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imagemAssetUrl(slide.id)}
          alt={`slide ${slide.n}${slide.funcao ? ` — ${slide.funcao}` : ''}`}
          className="h-full w-full object-cover"
          draggable={false}
        />
      )}

      {total > 1 && (
        <>
          <button
            type="button"
            aria-label="slide anterior"
            onClick={() => ir(-1)}
            className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-carbon-900/70 p-2 font-display text-neutral-100 opacity-0 backdrop-blur-sm transition-opacity hover:bg-carbon-900/90 group-hover:opacity-100"
          >
            ‹
          </button>
          <button
            type="button"
            aria-label="próximo slide"
            onClick={() => ir(1)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-carbon-900/70 p-2 font-display text-neutral-100 opacity-0 backdrop-blur-sm transition-opacity hover:bg-carbon-900/90 group-hover:opacity-100"
          >
            ›
          </button>

          {/* contador */}
          <span className="absolute right-2.5 top-2.5 rounded-full bg-carbon-900/70 px-2 py-0.5 font-display text-[11px] font-medium text-neutral-200 backdrop-blur-sm">
            {slide.n} / {total}
          </span>

          {/* dots */}
          <div className="absolute inset-x-0 bottom-2.5 flex items-center justify-center gap-1.5">
            {slides.map((s, idx) => (
              <button
                key={s.id}
                type="button"
                aria-label={`ir para slide ${s.n}`}
                onClick={() => setI(idx)}
                className={`h-1.5 rounded-full transition-all ${
                  idx === i ? 'w-4 bg-electric' : 'w-1.5 bg-neutral-100/40 hover:bg-neutral-100/70'
                }`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
