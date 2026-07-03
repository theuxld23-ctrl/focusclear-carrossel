"""Nó — REEL COMPOSITOR. Monta o vídeo final do reel (9:16, 1080×1920, MP4).

Costura REAL com ffmpeg (briefing 4B): intercala o avatar (talking-head do HeyGen
falando o roteiro) com fotos reais do momento (mesma cascata do carrossel) como
b-roll nos beats de tensão, com a narração (ElevenLabs) por cima e LEGENDAS
queimadas desde o frame 1 + label "conteúdo gerado por IA" no canto.

Estratégia de montagem (em ordem):
  1. **ffmpeg (default confiável)** — quando há avatar + áudio: segmenta por beat
     (avatar ↔ b-roll), queima legenda/label por segmento, concatena e faz o mux
     da narração. É o caminho principal. `montar_ffmpeg`.
  2. Palmier MCP — alternativa quando o app do editor está aberto (detecção via
     `_palmier_disponivel`; a montagem via MCP não é implementada aqui — ffmpeg é o
     default).
  3. Placeholder — sem avatar/áudio (chaves vazias) OU sem ffmpeg: grava um webm
     9:16 do poster com o Chromium do Playwright. Sempre funciona, sem chaves.

ffmpeg é resolvido do PATH do sistema ou do binário estático do `imageio-ffmpeg`
(local, sem rede). NÃO conecta HeyGen/ElevenLabs — recebe os arquivos que os nós
`avatar.py`/`voz.py` já produzem quando têm chave.

Todo reel também ganha um poster PNG 9:16 e um manifest.json (o plano do reel).
Não toca nos nós de carrossel/motion. Costuras injetáveis `montar(reel, state)`,
`render_overlay` e `baixar_foto` permitem provar a montagem offline (mocks).
"""
from __future__ import annotations

import base64
import html as _html
import json
import subprocess
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


def _ffmpeg_bin() -> Optional[str]:
    """Caminho do ffmpeg: PATH do sistema ou binário estático do imageio-ffmpeg."""
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 — sem ffmpeg → o chamador cai pro placeholder
        return None


# ── Montagem REAL com ffmpeg (avatar ↔ b-roll + narração + legendas) ──────────
FPS = 30
_DUR_PADRAO_S = 35.0
# Beats que viram B-ROLL (foto real do momento) enquanto a narração continua; os
# demais mostram o avatar. Intercala talking-head ↔ fotos na tensão (briefing 4B).
_BEATS_BROLL = {"tensao", "espelho"}
# Preenche 1080×1920 sem distorcer (cobre e corta o excedente).
_VF_FILL = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"


def _plano_beats(reel: dict) -> list[dict]:
    """Divide a duração entre os beats (proporcional às palavras) e marca b-roll."""
    r = reel.get("roteiro") or {}
    beats = [b for b in r.get("beats", []) if (b.get("texto") or "").strip()]
    if not beats:
        return []
    total = float(r.get("duracao_estimada_s") or _DUR_PADRAO_S)
    total = max(15.0, min(total, 60.0))
    pesos = [max(1, len((b.get("texto") or "").split())) for b in beats]
    soma = sum(pesos)
    plano: list[dict] = []
    for b, w in zip(beats, pesos):
        plano.append({
            "beat": b.get("beat"),
            "texto": b.get("texto", ""),
            "dur": max(1.5, round(total * w / soma, 2)),
            "broll": b.get("beat") in _BEATS_BROLL,
        })
    return plano


def _overlay_html(texto: str, label: str) -> str:
    """Overlay transparente 9:16: legenda queimada (rodapé) + label IA (canto)."""
    cap = _html.escape(texto)
    lab = _html.escape(label)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    {_fontfaces()}
    *{{margin:0;padding:0;box-sizing:border-box}}
    html,body{{width:{W}px;height:{H}px;background:transparent;overflow:hidden}}
    .wrap{{position:relative;width:{W}px;height:{H}px;font-family:'Big Shoulders Display',sans-serif}}
    .ia{{position:absolute;top:{SAFE - 40}px;right:60px;font-family:'Young Serif',serif;font-size:26px;
      color:#F2EBDD;background:rgba(13,11,15,.60);border:1px solid rgba(227,168,124,.6);
      border-radius:999px;padding:10px 22px}}
    .cap{{position:absolute;left:60px;right:60px;bottom:{SAFE}px;
      background:linear-gradient(0deg, rgba(13,11,15,.86), rgba(13,11,15,.52));
      border-left:8px solid #FF5436;border-radius:16px;padding:28px 32px;
      font-weight:800;font-size:62px;line-height:1.04;text-transform:uppercase;color:#F2EBDD;
      text-align:center;text-shadow:0 3px 18px rgba(0,0,0,.65)}}
    </style></head><body><div class="wrap">
      <div class="ia">{lab}</div>
      <div class="cap">{cap}</div>
    </div></body></html>"""


def _render_overlay(html: str, destino: Path) -> str:
    """PNG transparente 1080×1920 da legenda+label (Playwright, offline)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.screenshot(path=str(destino), omit_background=True,
                        clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return str(destino)


def _run_ffmpeg(ffmpeg: str, args: list[str]) -> None:
    r = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {r.stderr.strip()[:400]}")


def _seg_avatar(ffmpeg: str, avatar: str, cursor: float, dur: float,
                overlay: str, destino: Path) -> None:
    """Segmento do avatar: recorta a fatia [cursor, cursor+dur] (looping se curto),
    preenche 9:16 e queima o overlay. Mantém o lip-sync alinhado à narração."""
    fc = (f"[0:v]trim=start={cursor}:duration={dur},setpts=PTS-STARTPTS,"
          f"{_VF_FILL},fps={FPS}[b];[b][1:v]overlay=0:0[v]")
    _run_ffmpeg(ffmpeg, [
        "-stream_loop", "-1", "-i", avatar, "-i", overlay,
        "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}",
        "-r", f"{FPS}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
        "-an", str(destino),
    ])


def _seg_foto(ffmpeg: str, foto: str, dur: float, overlay: str, destino: Path) -> None:
    """Segmento de b-roll: foto real por `dur`s, preenche 9:16 e queima o overlay."""
    fc = f"[0:v]{_VF_FILL},fps={FPS}[b];[b][1:v]overlay=0:0[v]"
    _run_ffmpeg(ffmpeg, [
        "-loop", "1", "-t", f"{dur}", "-i", foto, "-i", overlay,
        "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}",
        "-r", f"{FPS}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
        "-an", str(destino),
    ])


def _concat_mux(ffmpeg: str, segs: list[Path], audio: str, destino: Path) -> str:
    """Concatena os segmentos (vídeo) e faz o mux da narração por cima (MP4 final)."""
    lista = destino.parent / "_segs.txt"
    lista.write_text("".join(f"file '{s.resolve()}'\n" for s in segs), encoding="utf-8")
    mudo = destino.parent / "_mudo.mp4"
    _run_ffmpeg(ffmpeg, ["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)])
    _run_ffmpeg(ffmpeg, [
        "-i", str(mudo), "-i", audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(destino),
    ])
    return str(destino)


def _baixar_foto(url: str) -> Optional[bytes]:
    r = requests.get(url, timeout=15)
    return r.content if r.status_code == 200 else None


def _preparar_fotos(reel: dict, state: dict,
                    baixar: Optional[Callable[[str], Optional[bytes]]] = None) -> list[str]:
    """Fotos reais p/ b-roll: usa reel['_fotos'] se dado (testes), senão baixa as
    top imagens do catálogo da cascata (state['imagens_por_jogo']) do momento."""
    presets = reel.get("_fotos")
    if presets:
        return [f for f in presets if Path(f).is_file()]
    from engine.nodes.coleta_imagens import jogo_key
    cat = (state.get("imagens_por_jogo") or {}).get(jogo_key(reel.get("_jogo", {})), [])
    urls = [i.get("url") for i in cat if i.get("url")][:3]
    if not urls:
        return []
    baixar = baixar or _baixar_foto
    destino = Path(reel["_dir"])
    destino.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    for idx, u in enumerate(urls):
        try:
            dados = baixar(u)
        except Exception:  # noqa: BLE001 — uma foto que falha não derruba a montagem
            dados = None
        if dados:
            p = destino / f"broll_{idx}.jpg"
            p.write_bytes(dados)
            out.append(str(p))
    return out


def montar_ffmpeg(
    reel: dict,
    state: dict,
    ffmpeg: Optional[str] = None,
    render_overlay: Optional[Callable[[str, Path], str]] = None,
    baixar_foto: Optional[Callable[[str], Optional[bytes]]] = None,
) -> Optional[str]:
    """Montagem REAL (ffmpeg): avatar ↔ b-roll + narração + legendas → MP4 9:16.

    Retorna o caminho do MP4 montado, ou None quando não dá pra montar (sem ffmpeg,
    ou faltando avatar/áudio) — nesse caso o chamador cai pro placeholder.
    """
    ffmpeg = ffmpeg or _ffmpeg_bin()
    if not ffmpeg:
        return None
    avatar, audio = reel.get("_avatar_video"), reel.get("_audio")
    if not (avatar and audio and Path(avatar).is_file() and Path(audio).is_file()):
        return None

    render_overlay = render_overlay or _render_overlay
    label = (reel.get("roteiro") or {}).get("label_ia", "conteúdo gerado por IA")
    plano = _plano_beats(reel)
    if not plano:
        return None

    destino = Path(reel["_dir"])
    seg_dir = destino / "segs"
    seg_dir.mkdir(parents=True, exist_ok=True)
    fotos = _preparar_fotos(reel, state, baixar_foto)

    segs: list[Path] = []
    cursor = 0.0
    foto_i = 0
    for i, p in enumerate(plano):
        overlay = render_overlay(_overlay_html(p["texto"], label), seg_dir / f"ov_{i}.png")
        seg = seg_dir / f"seg_{i}.mp4"
        if p["broll"] and fotos:
            _seg_foto(ffmpeg, fotos[foto_i % len(fotos)], p["dur"], overlay, seg)
            foto_i += 1
        else:
            _seg_avatar(ffmpeg, avatar, cursor, p["dur"], overlay, seg)
        segs.append(seg)
        cursor += p["dur"]

    mp4 = _concat_mux(ffmpeg, segs, audio, destino / "reel.mp4")
    reel["_segmentos"] = [str(s) for s in segs]
    reel["_broll_usadas"] = fotos
    return mp4


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
    """Retorna (caminho_video | None, placeholder?). ffmpeg (real) → placeholder webm."""
    destino = Path(reel["_dir"])
    tem_media = bool(reel.get("_avatar_video") and reel.get("_audio"))

    # 1. Montagem REAL com ffmpeg (default confiável) quando há avatar + áudio.
    if tem_media:
        try:
            mp4 = montar_ffmpeg(reel, state)
            if mp4:
                return mp4, False  # vídeo montado de verdade — NÃO é placeholder
            print("[reel] ffmpeg indisponível — caindo pro placeholder")
        except Exception as e:  # noqa: BLE001 — montagem falhou, cai pro placeholder
            print(f"[reel] montagem ffmpeg falhou: {e!r} — usando placeholder")

    # 2. Palmier MCP é alternativa quando o app do editor está aberto (ffmpeg é o
    #    default; a montagem via MCP não é implementada aqui). Só detecta e loga.
    if tem_media and _palmier_disponivel():  # pragma: no cover - requer app aberto
        print("[reel] Palmier MCP disponível (alternativa) — usando ffmpeg como default")

    # 3. placeholder garantido: webm 9:16 do poster (sem chaves / sem ffmpeg).
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
