"""Nó — VOZ (ElevenLabs). Gera o áudio PT-BR da fala do reel.

Sem ELEVENLABS_API_KEY → PULA em silêncio (log, sem erro); o reel_compositor
segue com placeholder (legendas + b-roll, sem narração). Costura injetável
`sintetizar(texto) -> bytes` permite testar sem rede.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import requests

import config

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


def _sintetizador(api_key: str, voice_id: str) -> Callable[[str], bytes]:
    """Sintetizador real ElevenLabs: texto PT-BR -> mp3 bytes."""
    def sintetizar(texto: str) -> bytes:
        r = requests.post(
            f"{_TTS_URL}/{voice_id}",
            headers={"xi-api-key": api_key, "accept": "audio/mpeg"},
            json={
                "text": texto,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.content

    return sintetizar


def gerar_voz(
    state: dict,
    sintetizar: Optional[Callable[[str], bytes]] = None,
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> dict:
    """Preenche reel['_audio'] (path do mp3) por reel; no-op se sem chave."""
    api_key = api_key if api_key is not None else config.ELEVENLABS_API_KEY
    # voice_id do personagem (banco, via state) tem prioridade sobre o .env.
    if voice_id is None:
        voice_id = (state.get("voz_config") or {}).get("voice_id") or config.ELEVENLABS_VOICE_ID

    if not sintetizar and not api_key:
        print("[voz] ELEVENLABS_API_KEY ausente — pulando (reel sai sem narração)")
        for reel in state.get("reels_prontos", []):
            reel["_audio"] = None
        return state

    sintetizar = sintetizar or _sintetizador(api_key, voice_id or "Rachel")
    erros = state.setdefault("erros", [])

    for reel in state.get("reels_prontos", []):
        reel["_audio"] = None
        texto = (reel.get("roteiro") or {}).get("texto_completo", "")
        if not texto:
            continue
        try:
            audio = sintetizar(texto)
            destino = Path(reel["_dir"])
            destino.mkdir(parents=True, exist_ok=True)
            arq = destino / "voz.mp3"
            arq.write_bytes(audio)
            reel["_audio"] = str(arq)
        except Exception as e:  # noqa: BLE001 — falha de voz não derruba o reel
            erros.append(f"voz falhou p/ {reel.get('momento')!r}: {e!r}")

    return state
