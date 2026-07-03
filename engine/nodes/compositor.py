"""Nó 6 — COMPOSITOR. Monta o HTML de cada slide e renderiza PNG 1080×1350.

Jornada escuro→luz em 8 (ou 6) slides. Tipografia Big Shoulders Display (display)
+ Young Serif (virada/sub), fontes EMBUTIDAS em base64 (render 100% offline).
Paleta brasa: brasa-noite #0D0B0F, refletor #F2EBDD, brasa #FF5436, pele #E3A87C.

Safe-zone: todo texto crítico fica no quadrado central 1080×1080 (135px de respiro
no topo e na base) — no grid do perfil o 4:5 é cortado pra esse centro.

Playwright renderiza cada slide → engine/output/<carrossel>/slide_N.png. Costura
injetável `render` (list[html] -> list[png_bytes]) permite trocar o renderizador.
"""
from __future__ import annotations

import base64
import html as _html
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional

from config import OUTPUT

_FONTS_DIR = Path(__file__).resolve().parent.parent / "templates" / "fonts"
W, H = 1080, 1350
SAFE = 135  # respiro topo/base → quadrado central 1080×1080

_GRUPO = {
    "gancho": "escuro", "dado": "escuro", "espelho": "escuro",
    "participacao": "transicao",
    "virada": "luz", "prova": "luz", "alivio": "luz", "cta": "luz",
}


def _font_b64(nome: str) -> str:
    return base64.b64encode((_FONTS_DIR / nome).read_bytes()).decode("ascii")


def _fontfaces() -> str:
    big = _font_b64("BigShouldersDisplay.woff2")
    serif = _font_b64("YoungSerif-400.woff2")
    return f"""
    @font-face {{ font-family:'Big Shoulders Display'; font-weight:400 900; font-display:block;
      src:url(data:font/woff2;base64,{big}) format('woff2'); }}
    @font-face {{ font-family:'Young Serif'; font-weight:400; font-display:block;
      src:url(data:font/woff2;base64,{serif}) format('woff2'); }}
    """


# cache dos font-faces (lê os arquivos uma vez)
_FONTFACES_CACHE: Optional[str] = None


def _fontfaces_cached() -> str:
    global _FONTFACES_CACHE
    if _FONTFACES_CACHE is None:
        _FONTFACES_CACHE = _fontfaces()
    return _FONTFACES_CACHE


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "carrossel"


def _tamanho_headline(headline: str) -> int:
    linhas = (headline or "").split("\n")
    maior = max((len(l) for l in linhas), default=0)
    if maior <= 16:
        return 132
    if maior <= 26:
        return 104
    if maior <= 38:
        return 82
    return 64


def _headline_html(headline: str, destaque: Optional[str]) -> str:
    """Escapa a headline, realça a palavra-destaque (brasa) e converte \\n em <br>."""
    texto = headline or ""
    if destaque:
        idx = texto.lower().find(destaque.lower())
        if idx >= 0:
            antes, meio, depois = (
                texto[:idx],
                texto[idx : idx + len(destaque)],
                texto[idx + len(destaque) :],
            )
            montado = (
                _html.escape(antes)
                + f'<span class="brasa">{_html.escape(meio)}</span>'
                + _html.escape(depois)
            )
            return montado.replace("\n", "<br>")
    return _html.escape(texto).replace("\n", "<br>")


def _bloco_extra(slide: dict) -> str:
    """Elementos por função: opções (participação), micro-CTA (alívio), handle (CTA)."""
    func = slide.get("funcao", "")
    if func == "participacao":
        opcoes = slide.get("opcoes") or []
        pills = "".join(f'<div class="pill">{_html.escape(str(o))}</div>' for o in opcoes)
        marca = '<div class="marca">marca um amigo 👇</div>'
        return f'<div class="opcoes">{pills}</div>{marca}'
    if func == "alivio":
        mc = slide.get("micro_cta_salvar") or "salva isso pra quando precisar lembrar"
        return f'<div class="microcta">🔖 {_html.escape(str(mc))}</div>'
    if func == "cta":
        return '<div class="handle">@focusclear</div>'
    return ""


def build_html(slide: dict) -> str:
    func = slide.get("funcao", "")
    grupo = _GRUPO.get(func, "escuro")
    kicker = _html.escape(slide.get("kicker", "") or "")
    sub = _html.escape(slide.get("sub", "") or "")
    headline = _headline_html(slide.get("headline", ""), slide.get("palavra_destaque"))
    fs = _tamanho_headline(slide.get("headline", ""))
    contador = f'{slide.get("n", "")}'

    bg = slide.get("_bg")
    if bg:
        camada_bg = f'<div class="bg" style="background-image:url(data:image/png;base64,{bg})"></div>'
    else:
        camada_bg = '<div class="bg tipografico"></div>'

    extra = _bloco_extra(slide)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    {_fontfaces_cached()}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html,body {{ width:{W}px; height:{H}px; overflow:hidden; }}
    .slide {{ position:relative; width:{W}px; height:{H}px;
      font-family:'Big Shoulders Display',system-ui,sans-serif; }}
    .slide.escuro {{ background:#0D0B0F; --fg:#F2EBDD; --sub:#E3A87C; }}
    .slide.transicao {{ background:linear-gradient(180deg,#0D0B0F 0%,#2a1a16 100%); --fg:#F2EBDD; --sub:#E3A87C; }}
    .slide.luz {{ background:#F2EBDD; --fg:#0D0B0F; --sub:#9a4a34; }}
    .bg {{ position:absolute; inset:0; background-size:cover; background-position:center; }}
    .bg.tipografico {{ background:
        radial-gradient(120% 80% at 50% 18%, rgba(255,84,54,.18), transparent 60%); }}
    .scrim {{ position:absolute; inset:0; }}
    .escuro .scrim {{ background:linear-gradient(180deg, rgba(13,11,15,.20) 0%, rgba(13,11,15,.55) 45%, rgba(13,11,15,.94) 100%); }}
    .transicao .scrim {{ background:linear-gradient(180deg, rgba(13,11,15,.15) 0%, rgba(42,26,22,.55) 50%, rgba(13,11,15,.90) 100%); }}
    .luz .scrim {{ background:linear-gradient(180deg, rgba(242,235,221,.10) 0%, rgba(242,235,221,.55) 45%, rgba(242,235,221,.96) 100%); }}
    .safe {{ position:absolute; left:0; right:0; top:{SAFE}px; height:{H - 2*SAFE}px;
      padding:64px 72px; display:flex; flex-direction:column; justify-content:space-between; }}
    .topo {{ display:flex; justify-content:space-between; align-items:flex-start; }}
    .kicker {{ font-weight:700; font-size:26px; letter-spacing:.18em; text-transform:uppercase;
      color:#FF5436; }}
    .contador {{ font-weight:700; font-size:24px; letter-spacing:.1em; color:var(--sub); opacity:.8; }}
    .fundo {{ display:flex; flex-direction:column; gap:26px; }}
    .headline {{ font-weight:800; font-size:{fs}px; line-height:.94; text-transform:uppercase;
      color:var(--fg); letter-spacing:-.01em; }}
    .headline .brasa {{ color:#FF5436; }}
    .sub {{ font-family:'Young Serif',Georgia,serif; font-size:34px; line-height:1.28; color:var(--sub); max-width:820px; }}
    .opcoes {{ display:flex; flex-direction:column; gap:16px; margin-top:8px; }}
    .pill {{ font-weight:700; font-size:34px; text-transform:uppercase; color:var(--fg);
      border:2px solid rgba(255,84,54,.55); border-radius:16px; padding:18px 26px; }}
    .marca {{ font-family:'Young Serif',serif; font-size:28px; color:var(--sub); margin-top:6px; }}
    .microcta {{ font-family:'Young Serif',serif; font-size:26px; color:var(--sub); }}
    .handle {{ font-weight:800; font-size:56px; color:#FF5436; letter-spacing:.02em; }}
    </style></head><body>
    <div class="slide {grupo}">
      {camada_bg}
      <div class="scrim"></div>
      <div class="safe">
        <div class="topo">
          <div class="kicker">{kicker}</div>
          <div class="contador">{contador}</div>
        </div>
        <div class="fundo">
          <div class="headline">{headline}</div>
          {f'<div class="sub">{sub}</div>' if sub else ''}
          {extra}
        </div>
      </div>
    </div></body></html>"""


def _render_pngs(htmls: list[str]) -> list[bytes]:
    """Renderiza cada HTML em PNG 1080×1350 com Playwright (Chromium local, offline)."""
    from playwright.sync_api import sync_playwright

    pngs: list[bytes] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for h in htmls:
            page.set_content(h, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            pngs.append(page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}))
        browser.close()
    return pngs


def compor(
    state: dict,
    render: Optional[Callable[[list[str]], list[bytes]]] = None,
) -> dict:
    """Renderiza os PNGs de cada carrossel pronto em engine/output/<carrossel>/."""
    render = render or _render_pngs

    for i, roteiro in enumerate(state.get("carrosseis_prontos", [])):
        slides = roteiro.get("slides", [])
        if not slides:
            continue
        jogo = roteiro.get("_jogo", {})
        times = "-".join(jogo.get("times", []) or ["carrossel"])
        nome = _slug(f"{state.get('data','')}-{roteiro.get('_perfil','')}-{times}-{i}")
        destino = OUTPUT / nome
        destino.mkdir(parents=True, exist_ok=True)

        htmls = [build_html(s) for s in slides]
        pngs = render(htmls)

        caminhos: list[str] = []
        for slide, png in zip(slides, pngs):
            arq = destino / f"slide_{slide.get('n')}.png"
            arq.write_bytes(png)
            slide["_png"] = str(arq)
            caminhos.append(str(arq))
        roteiro["_pngs"] = caminhos
        roteiro["_dir"] = str(destino)

    return state
