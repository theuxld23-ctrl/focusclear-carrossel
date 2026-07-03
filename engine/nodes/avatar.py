"""Nó — AVATAR (HeyGen). Gera o talking-head (foto + áudio → vídeo lip-sync).

Avatar FICTÍCIO fixo do FocusClear (decisão travada: não é clone de pessoa real).
Sem HEYGEN_API_KEY → PULA em silêncio (log, sem erro). Também pula se não houver
áudio (a voz foi pulada) — sem áudio não há lip-sync. O reel_compositor então
segue só com b-roll + legendas (placeholder).

Costura injetável `gerar(foto, audio) -> bytes` permite testar sem rede.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import requests

import config

_HEYGEN = "https://api.heygen.com/v2"


def _foto_referencia(state: dict) -> Optional[str]:
    """Foto do avatar: do state, ou o upload em engine/assets/personagem_*."""
    foto = state.get("avatar_foto")
    if foto and Path(foto).is_file():
        return foto
    for ext in (".png", ".jpg", ".webp"):
        p = config.ASSETS / f"personagem_focusclear{ext}"
        if p.is_file():
            return str(p)
    return None


def _gerador(api_key: str) -> Callable[[str, str], bytes]:
    """Gerador real HeyGen (talking photo). Best-effort submit+poll+download."""
    def gerar(foto: str, audio: str) -> bytes:  # pragma: no cover - requer rede/chave
        headers = {"X-Api-Key": api_key}
        # (esboço do fluxo v2 — só roda com chave real; offline é sempre pulado)
        r = requests.post(f"{_HEYGEN}/video/generate", headers=headers, json={
            "video_inputs": [{
                "character": {"type": "talking_photo", "talking_photo_url": foto},
                "voice": {"type": "audio", "audio_url": audio},
            }],
            "dimension": {"width": 1080, "height": 1920},
        }, timeout=60)
        r.raise_for_status()
        vid = r.json()["data"]["video_id"]
        # poll simplificado
        for _ in range(60):
            s = requests.get(f"{_HEYGEN}/video_status.get?video_id={vid}",
                             headers=headers, timeout=30).json()
            if s.get("data", {}).get("status") == "completed":
                url = s["data"]["video_url"]
                return requests.get(url, timeout=120).content
        raise RuntimeError("HeyGen timeout")

    return gerar


def gerar_avatar(
    state: dict,
    gerar: Optional[Callable[[str, str], bytes]] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Preenche reel['_avatar_video'] (path mp4) por reel; no-op se sem chave/áudio."""
    api_key = api_key if api_key is not None else config.HEYGEN_API_KEY

    if not gerar and not api_key:
        print("[avatar] HEYGEN_API_KEY ausente — pulando (reel sai só com b-roll)")
        for reel in state.get("reels_prontos", []):
            reel["_avatar_video"] = None
        return state

    gerar = gerar or _gerador(api_key)
    foto = _foto_referencia(state)
    erros = state.setdefault("erros", [])

    for reel in state.get("reels_prontos", []):
        reel["_avatar_video"] = None
        audio = reel.get("_audio")
        if not audio:
            print("[avatar] reel sem áudio — pulando talking-head")
            continue
        if not foto:
            erros.append("avatar: sem foto de referência (engine/assets/personagem_*)")
            continue
        try:
            video = gerar(foto, audio)
            destino = Path(reel["_dir"])
            destino.mkdir(parents=True, exist_ok=True)
            arq = destino / "avatar.mp4"
            arq.write_bytes(video)
            reel["_avatar_video"] = str(arq)
        except Exception as e:  # noqa: BLE001 — falha do avatar não derruba o reel
            erros.append(f"avatar falhou p/ {reel.get('momento')!r}: {e!r}")

    return state
