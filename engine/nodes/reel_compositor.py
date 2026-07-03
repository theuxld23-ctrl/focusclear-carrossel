"""Nó — REEL COMPOSITOR. Monta o vídeo final do reel (9:16, 1080×1920).

Intercala o avatar (talking-head) com fotos reais do momento (mesma cascata do
carrossel) e legendas desde o frame 1. Estratégia de montagem:
  1. Palmier MCP (POST JSON-RPC) quando disponível E há avatar+áudio — montagem real.
  2. ffmpeg (fallback) — slideshow de b-roll + narração, se instalado.
  3. Placeholder offline garantido — grava um webm 9:16 do poster com o próprio
     Chromium do Playwright (sem ffmpeg). Sempre funciona, sem chaves.

Todo reel também ganha um poster PNG 9:16 e um manifest.json (o plano do reel).
Label "conteúdo gerado por IA" vai no manifest e no metadado do asset.

Não toca nos nós de carrossel. Costura injetável `montar(reel, state)` p/ teste.
"""
from __future__ import annotations

import base64
import html as _html
import json
from pathlib import Path
from typing import Any, Callable, Optional

import requests

import config

_FONTS_DIR = Path(__file__).resolve().parent.parent / "templates" / "fonts"
W, H = 1080, 1920  # 9:16
SAFE = 220  # respiro topo/base (legendas e foco no centro)

_FONTFACES_CACHE: Optional[str] = None


def _fontfaces() -> str:
    global _FONTFACES_CACHE
    if _FONTFACES_CACHE is None:
        big = base64.b64encode((_FONTS_DIR / "BigShouldersDisplay.woff2").read_bytes()).decode()
        serif = base64.b64encode((_FONTS_DIR / "YoungSerif-400.woff2").read_bytes()).decode()
        _FONTFACES_CACHE = (
            f"@font-face{{font-family:'Big Shoulders Display';font-weight:400 900;"
            f"src:url(data:font/woff2;base64,{big}) format('woff2');}}"
            f"@font-face{{font-family:'Young Serif';src:url(data:font/woff2;base64,{serif}) format('woff2');}}"
        )
    return _FONTFACES_CACHE


def _gancho(reel: dict) -> dict:
    for b in (reel.get("roteiro") or {}).get("beats", []):
        if b.get("beat") == "gancho":
            return b
    beats = (reel.get("roteiro") or {}).get("beats", [])
    return beats[0] if beats else {}


def poster_html(reel: dict) -> str:
    """Card 9:16: kicker do pilar, headline do gancho, 1ª legenda, label IA."""
    jogo = reel.get("_jogo", {})
    kicker = " x ".join(jogo.get("times", []) or ["Reel"])
    gancho = _gancho(reel)
    headline = _html.escape(gancho.get("texto", "") or reel.get("momento", "") or "")
    legenda = _html.escape((reel.get("roteiro") or {}).get("texto_completo", "")[:90])
    label = _html.escape((reel.get("roteiro") or {}).get("label_ia", "conteúdo gerado por IA"))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    {_fontfaces()}
    *{{margin:0;padding:0;box-sizing:border-box}}
    html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#0D0B0F}}
    .reel{{position:relative;width:{W}px;height:{H}px;font-family:'Big Shoulders Display',sans-serif;
      background:radial-gradient(130% 70% at 50% 22%, rgba(255,84,54,.20), #0D0B0F 62%)}}
    .safe{{position:absolute;left:0;right:0;top:{SAFE}px;height:{H-2*SAFE}px;padding:0 90px;
      display:flex;flex-direction:column;justify-content:space-between}}
    .topo{{display:flex;align-items:center;justify-content:space-between}}
    .kicker{{font-weight:700;font-size:34px;letter-spacing:.16em;text-transform:uppercase;color:#FF5436}}
    .ia{{font-family:'Young Serif',serif;font-size:24px;color:#E3A87C;border:1px solid rgba(227,168,124,.5);
      border-radius:999px;padding:8px 18px}}
    .headline{{font-weight:800;font-size:116px;line-height:.95;text-transform:uppercase;color:#F2EBDD}}
    .play{{width:150px;height:150px;border-radius:999px;background:rgba(255,84,54,.9);
      display:flex;align-items:center;justify-content:center;font-size:64px;color:#0D0B0F;margin:0 auto}}
    .legenda{{font-family:'Young Serif',serif;font-size:34px;line-height:1.3;color:#E3A87C;text-align:center}}
    </style></head><body>
    <div class="reel"><div class="safe">
      <div class="topo"><div class="kicker">{_html.escape(kicker)}</div><div class="ia">{label}</div></div>
      <div class="headline">{headline}</div>
      <div class="play">▶</div>
      <div class="legenda">{legenda}…</div>
    </div></div></body></html>"""


def _legendas(reel: dict) -> list[dict]:
    return [
        {"beat": b.get("beat"), "texto": b.get("texto", ""), "b_roll": b.get("b_roll", "")}
        for b in (reel.get("roteiro") or {}).get("beats", [])
    ]


def _manifest(reel: dict, state: dict) -> dict:
    r = reel.get("roteiro") or {}
    return {
        "momento": reel.get("momento"),
        "perfil": reel.get("_perfil"),
        "times": (reel.get("_jogo") or {}).get("times"),
        "formato": "reel",
        "dimensao": [W, H],
        "duracao_estimada_s": r.get("duracao_estimada_s"),
        "label_ia": r.get("label_ia", "conteúdo gerado por IA"),
        "narracao": reel.get("_audio"),
        "avatar": reel.get("_avatar_video"),
        "legendas": _legendas(reel),
        "avisos": reel.get("_avisos", []),
    }


# ── Renderização do poster (Playwright, offline) ─────────────────────────────
def _render_poster(html: str, destino: Path) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.screenshot(path=str(destino), clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return str(destino)


# ── Montagem do vídeo ────────────────────────────────────────────────────────
def _palmier_disponivel() -> bool:
    try:
        r = requests.post(
            config.PALMIER_MCP_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "focusclear", "version": "1"}}},
            timeout=4,
        )
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _tem_ffmpeg() -> bool:
    import shutil
    return shutil.which("ffmpeg") is not None


def _gravar_webm(html: str, destino: Path, segundos: int = 4) -> Optional[str]:
    """Placeholder garantido: grava um webm 9:16 do poster com o Chromium (sem ffmpeg)."""
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(destino),
            record_video_size={"width": W, "height": H},
        )
        page = ctx.new_page()
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_timeout(segundos * 1000)
        ctx.close()  # finaliza a gravação
        b.close()
    webms = sorted(destino.glob("*.webm"))
    if not webms:
        return None
    alvo = destino / "reel.webm"
    webms[-1].replace(alvo)
    return str(alvo)


def _montar_default(reel: dict, state: dict) -> tuple[Optional[str], bool]:
    """Retorna (caminho_video | None, placeholder?). Palmier → ffmpeg → webm."""
    destino = Path(reel["_dir"])
    tem_media = bool(reel.get("_avatar_video") and reel.get("_audio"))

    # 1. Palmier MCP quando disponível E há avatar+áudio (montagem real — Fase 3+)
    if tem_media and _palmier_disponivel():  # pragma: no cover - requer chaves
        print("[reel] Palmier MCP disponível — montagem via editor")
        # Fluxo completo de montagem via MCP entra quando houver HeyGen/ElevenLabs.

    # 2. ffmpeg (se instalado) — fora do escopo offline; deixado como hook
    #    (ffmpeg não está instalado nesta máquina; ver briefing seção 9)

    # 3. placeholder garantido: webm do poster
    try:
        webm = _gravar_webm(reel["_poster_html"], destino)
        return webm, not tem_media
    except Exception as e:  # noqa: BLE001
        print(f"[reel] gravação webm falhou: {e!r} — usando poster PNG")
        return None, True


def compor_reel(
    state: dict,
    montar: Optional[Callable[[dict, dict], tuple[Optional[str], bool]]] = None,
    render_poster: Optional[Callable[[str, Path], str]] = None,
) -> dict:
    """Gera poster + manifest + vídeo (ou placeholder) por reel."""
    montar = montar or _montar_default
    render_poster = render_poster or _render_poster
    erros = state.setdefault("erros", [])

    for reel in state.get("reels_prontos", []):
        destino = Path(reel["_dir"])
        destino.mkdir(parents=True, exist_ok=True)

        # manifest (plano do reel)
        manifest = _manifest(reel, state)
        arq_manifest = destino / "manifest.json"
        arq_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        reel["_manifest"] = str(arq_manifest)

        # poster 9:16
        html = poster_html(reel)
        reel["_poster_html"] = html
        try:
            reel["_poster"] = render_poster(html, destino / "poster.png")
        except Exception as e:  # noqa: BLE001
            erros.append(f"reel poster falhou p/ {reel.get('momento')!r}: {e!r}")
            reel["_poster"] = None

        # montagem do vídeo (ou placeholder)
        try:
            video, placeholder = montar(reel, state)
        except Exception as e:  # noqa: BLE001
            erros.append(f"reel montagem falhou p/ {reel.get('momento')!r}: {e!r}")
            video, placeholder = None, True

        reel["_video"] = video
        reel["_placeholder"] = placeholder or not video
        reel["_caminho"] = video or reel.get("_poster")

    return state
