"""Nó — MOTION COMPOSITOR. Carrossel com 1-2 slides em vídeo curto (motion).

Reaproveita o MESMO HTML dos slides do carrossel (importa build_html do
compositor — sem modificá-lo). Renderiza a maioria dos slides como PNG estático e
1-2 slides como webm com motion sutil (Ken Burns / parallax via CSS animation),
capturado pelo Chromium do Playwright. v1 NÃO usa Kling/Seedance.

Não toca nos nós de carrossel/reel. Costuras injetáveis `render_png` e
`gravar_webm` permitem testar sem custo de rede/gpu.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from config import OUTPUT
from engine.nodes.compositor import build_html, W, H, _slug

# Quais slides ganham motion (por número). Gancho e virada são os mais fortes.
_SLIDES_ANIMADOS = {1, 5}

_ANIMACAO_CSS = (
    "@keyframes kb{0%{transform:scale(1.0) translateY(0)}"
    "100%{transform:scale(1.14) translateY(-1.5%)}}"
    "@keyframes rise{0%{opacity:0;transform:translateY(26px)}"
    "60%{opacity:1}100%{opacity:1;transform:translateY(0)}}"
    ".bg{animation:kb 6s ease-in-out infinite alternate;transform-origin:50% 42%}"
    ".fundo{animation:rise 1.1s ease-out both}"
)


def _com_animacao(html: str) -> str:
    """Injeta o motion sutil no HTML do slide (Ken Burns no fundo + rise no texto)."""
    return html.replace("</style>", _ANIMACAO_CSS + "</style>")


def _render_png_default(html: str, destino: Path) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.screenshot(path=str(destino), clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return str(destino)


def _gravar_webm_default(html: str, destino_dir: Path, nome: str, segundos: int = 4) -> Optional[str]:
    """Grava o slide animado como webm 1080×1350 (Chromium, sem ffmpeg)."""
    from playwright.sync_api import sync_playwright

    destino_dir.mkdir(parents=True, exist_ok=True)
    origem = None
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(destino_dir),
            record_video_size={"width": W, "height": H},
        )
        page = ctx.new_page()
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_timeout(segundos * 1000)
        video = page.video
        ctx.close()  # finaliza a gravação
        # path() aponta EXATAMENTE este vídeo (evita colisão com webms já no dir)
        origem = Path(video.path()) if video else None
        b.close()
    if not origem or not origem.exists():
        return None
    alvo = destino_dir / nome
    origem.replace(alvo)
    return str(alvo)


def compor_motion(
    state: dict,
    render_png: Optional[Callable[[str, Path], str]] = None,
    gravar_webm: Optional[Callable[[str, Path, str], Optional[str]]] = None,
    animados: Optional[set[int]] = None,
) -> dict:
    """Gera slides mistos (PNG estático + webm animado) por carrossel pronto."""
    render_png = render_png or _render_png_default
    gravar_webm = gravar_webm or _gravar_webm_default
    animados = animados if animados is not None else _SLIDES_ANIMADOS
    erros = state.setdefault("erros", [])

    for i, roteiro in enumerate(state.get("carrosseis_prontos", [])):
        slides = roteiro.get("slides", [])
        if not slides:
            continue
        jogo = roteiro.get("_jogo", {})
        times = "-".join(jogo.get("times", []) or ["motion"])
        nome = _slug(f"motion-{state.get('data','')}-{roteiro.get('_perfil','')}-{times}-{i}")
        destino = OUTPUT / nome
        destino.mkdir(parents=True, exist_ok=True)

        caminhos: list[str] = []
        for slide in slides:
            n = slide.get("n")
            html = build_html(slide)
            slide["_animado"] = n in animados
            try:
                if slide["_animado"]:
                    caminho = gravar_webm(_com_animacao(html), destino, f"slide_{n}.webm")
                    if not caminho:  # fallback: estático se a gravação falhar
                        caminho = render_png(html, destino / f"slide_{n}.png")
                        slide["_animado"] = False
                else:
                    caminho = render_png(html, destino / f"slide_{n}.png")
            except Exception as e:  # noqa: BLE001
                erros.append(f"motion slide {n} falhou: {e!r}")
                caminho = None
            slide["_caminho"] = caminho
            if caminho:
                caminhos.append(caminho)

        roteiro["_dir"] = str(destino)
        roteiro["_caminhos"] = caminhos
        roteiro["_motion_animados"] = sorted(s.get("n") for s in slides if s.get("_animado"))

    return state
