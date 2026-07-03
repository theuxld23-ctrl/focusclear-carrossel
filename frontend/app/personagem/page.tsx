'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getPersonagem,
  salvarPersonagem,
  uploadFotoPersonagem,
  fotoPersonagemUrl,
} from '@/lib/api'

export default function PersonagemPage() {
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
  const [tom, setTom] = useState('')
  const [voiceId, setVoiceId] = useState('')
  const [temFoto, setTemFoto] = useState(false)
  const [bust, setBust] = useState(0) // cache-bust da foto após upload
  const [erro, setErro] = useState<string | null>(null)
  const [salvo, setSalvo] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const inputFoto = useRef<HTMLInputElement>(null)

  const carregar = useCallback(async () => {
    try {
      const p = await getPersonagem()
      setNome(p.nome || '')
      setDescricao(p.descricao || '')
      setTom(p.tom_de_voz || '')
      setVoiceId((p.config?.voice_id as string) || '')
      setTemFoto(Boolean(p.foto_ref))
      setBust(Date.now())
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  async function salvar() {
    setSalvando(true)
    setSalvo(false)
    try {
      await salvarPersonagem({ nome, descricao, tom_de_voz: tom, voice_id: voiceId })
      setSalvo(true)
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    } finally {
      setSalvando(false)
    }
  }

  async function enviarFoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadFotoPersonagem(file)
      setTemFoto(true)
      setBust(Date.now())
      setErro(null)
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-neutral-50">
          Personagem
        </h1>
        <p className="mt-1 font-body text-sm text-neutral-500">
          Config do avatar FocusClear — nome, descrição, tom de voz e foto de referência.
        </p>
      </div>

      {erro && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-body text-sm text-red-300">
          {erro}
        </p>
      )}

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Formulário */}
        <div className="card space-y-5 p-6">
          <div>
            <label className="label" htmlFor="nome">Nome</label>
            <input
              id="nome"
              className="input"
              placeholder="ex.: Foco"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="descricao">Descrição</label>
            <textarea
              id="descricao"
              className="input h-24"
              placeholder="quem é o avatar, aparência, personalidade"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="tom">Tom de voz</label>
            <textarea
              id="tom"
              className="input h-24"
              placeholder="ex.: acolhedor, direto, sem jargão clínico"
              value={tom}
              onChange={(e) => setTom(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="voice">
              Voice ID <span className="text-neutral-600">(ElevenLabs — reel)</span>
            </label>
            <input
              id="voice"
              className="input font-mono"
              placeholder="ex.: 21m00Tcm4TlvDq8ikWAM"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={salvar}
              disabled={salvando}
              className="rounded-lg bg-electric px-5 py-2.5 font-display text-sm font-semibold text-white transition-colors hover:bg-electric-soft disabled:opacity-50"
            >
              {salvando ? 'Salvando…' : 'Salvar'}
            </button>
            {salvo && <span className="font-body text-sm text-emerald-400">salvo ✓</span>}
          </div>
        </div>

        {/* Foto de referência + preview do avatar */}
        <div className="space-y-5">
          <div className="card p-5">
            <p className="label">Foto de referência</p>
            <div className="mb-3 flex aspect-square items-center justify-center overflow-hidden rounded-lg border border-carbon-600 bg-carbon-900">
              {temFoto ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={fotoPersonagemUrl(bust)}
                  alt="foto de referência"
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="font-body text-xs text-neutral-600">nenhuma foto</span>
              )}
            </div>
            <input
              ref={inputFoto}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={enviarFoto}
              className="hidden"
            />
            <button
              onClick={() => inputFoto.current?.click()}
              className="w-full rounded-lg border border-carbon-600 px-3 py-2 font-display text-sm font-medium text-neutral-300 transition-colors hover:bg-carbon-700"
            >
              {temFoto ? 'Trocar foto' : 'Enviar foto'}
            </button>
            <p className="mt-2 font-body text-xs text-neutral-600">
              salva local em engine/assets/ (sem upload externo)
            </p>
          </div>

          <div className="card flex aspect-square flex-col items-center justify-center gap-2 border-dashed p-5 text-center">
            <span className="font-display text-3xl">🎭</span>
            <p className="font-body text-xs text-neutral-500">
              avatar será gerado na <span className="text-electric">Fase 3</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
