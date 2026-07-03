"""FASE 3 + montagem real — pipeline de REEL (roteiro → voz → avatar → montagem), offline.

Roda com:  python -m tests.test_reel   (raiz, venv ativo)
Sucesso = asserções passam e imprime "REEL OK".

Dois caminhos provados sem NENHUMA API:
  - SEM chaves (voz/avatar pulam) → montar cai no placeholder (poster/webm 9:16);
  - COM avatar+áudio+fotos MOCKADOS (arquivos locais que os nós já produziriam) →
    o reel_compositor faz a COSTURA REAL com ffmpeg e sai um MP4 9:16 montado
    (avatar ↔ b-roll, narração por cima, legendas + label queimados). O ffmpeg é o
    binário estático do imageio-ffmpeg (local, sem rede).
Label "conteúdo gerado por IA" presente no manifest, no plano e queimado no vídeo.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from engine.nodes.roteirista_video import escrever_roteiro_video, checar_roteiro  # noqa: E402
from engine.nodes.voz import gerar_voz  # noqa: E402
from engine.nodes.avatar import gerar_avatar  # noqa: E402
from engine.nodes.reel_compositor import (  # noqa: E402
    compor_reel, montar_ffmpeg, _ffmpeg_bin, _run_ffmpeg, W, H,
)

APROVADO = {
    "momento": "Espanha 0x0 Cabo Verde — Vozinha (40) segura a Espanha",
    "fatos_confirmados": "Espanha 0x0 Cabo Verde; goleiro Vozinha, 40 anos, 5 defesas",
    "perfil": "ahsd", "subgeracao_alvo": "z_ponte", "angulo": None,
    "requer_revisao_medica": False,
    "_jogo": {"times": ["Espanha", "Cabo Verde"], "placar": "0x0",
              "narrativa": "Aos 40 anos, Vozinha segurou a Espanha."},
}


def _base_state():
    return {
        "turno": "manha", "pilar_ativo": "futebol", "data": "2026-06-15",
        "fase_copa": "grupos", "carrosseis_aprovados": [APROVADO], "erros": [],
    }


def roteirista_video_fake(system, user):
    assert "ADENDO" in system and "REEL" in system, "system deve derivar do roteirista.md + adendo vídeo"
    assert "Cabo Verde" in user and "ahsd" in user
    beats = [
        {"beat": "gancho", "texto": "Ele tinha 40 anos e ninguém dava nada por ele.", "b_roll": "Vozinha no gol", "palavras": 11},
        {"beat": "tensao", "texto": "A Espanha inteira vindo pra cima, e ele sozinho ali atrás.", "b_roll": "ataque espanhol"},
        {"beat": "espelho", "texto": "Tem gente que vive assim: provando o tempo todo que merece estar.", "b_roll": "closeup tenso"},
        {"beat": "virada_alivio", "texto": "Mas pertencer não se prova, se ocupa. E naquele dia ele ocupou.", "b_roll": "defesa e alívio"},
        {"beat": "cta_loop", "texto": "Segue a gente pra lembrar disso. Aos 40, ninguém dava nada — e ele segurou.", "b_roll": "comemoração"},
    ]
    return "```json\n" + json.dumps({
        "momento_usado": APROVADO["momento"], "perfil": "ahsd", "subgeracao": "z_ponte",
        "texto_completo": " ".join(b["texto"] for b in beats),
        "duracao_estimada_s": 38, "beats": beats,
        "label_ia": "conteúdo gerado por IA", "checagem_etica": "ok",
    }, ensure_ascii=False) + "\n```"


# ── Testes unitários ─────────────────────────────────────────────────────────
def test_roteiro_video_beats_e_gancho():
    state = escrever_roteiro_video(_base_state(), complete=roteirista_video_fake)
    reels = state["reels_prontos"]
    assert len(reels) == 1
    r = reels[0]["roteiro"]
    assert [b["beat"] for b in r["beats"]] == ["gancho", "tensao", "espelho", "virada_alivio", "cta_loop"]
    assert r["label_ia"] == "conteúdo gerado por IA"
    # gancho ≤ 14 palavras → sem aviso de gancho
    assert not any("gancho" in a for a in checar_roteiro(r)), checar_roteiro(r)


def test_voz_pula_sem_chave():
    state = escrever_roteiro_video(_base_state(), complete=roteirista_video_fake)
    state = gerar_voz(state, api_key="")  # sem chave
    assert state["reels_prontos"][0]["_audio"] is None


def test_avatar_pula_sem_chave():
    state = escrever_roteiro_video(_base_state(), complete=roteirista_video_fake)
    state = gerar_voz(state, api_key="")
    state = gerar_avatar(state, api_key="")  # sem chave
    assert state["reels_prontos"][0]["_avatar_video"] is None


# ── Pipeline reel → output placeholder ───────────────────────────────────────
def test_pipeline_reel_placeholder():
    state = escrever_roteiro_video(_base_state(), complete=roteirista_video_fake)
    state = gerar_voz(state, api_key="")       # pula
    state = gerar_avatar(state, api_key="")    # pula
    # monta injetado: sem vídeo → placeholder = poster
    state = compor_reel(state, montar=lambda reel, st: (None, True))

    reel = state["reels_prontos"][0]
    assert Path(reel["_manifest"]).exists(), "manifest não gerado"
    manifest = json.loads(Path(reel["_manifest"]).read_text(encoding="utf-8"))
    assert manifest["label_ia"] == "conteúdo gerado por IA"
    assert manifest["dimensao"] == [1080, 1920]
    assert len(manifest["legendas"]) == 5

    assert reel["_poster"] and Path(reel["_poster"]).exists(), "poster não gerado"
    assert Image.open(reel["_poster"]).size == (1080, 1920), "poster não é 9:16"
    assert reel["_caminho"] == reel["_poster"], "placeholder deve cair no poster"
    assert reel["_placeholder"] is True
    return reel


# ── Montagem REAL com ffmpeg (avatar+voz+b-roll+legendas → MP4), com mocks ───────
def _overlay_fake(html, destino):
    """render_overlay injetado: PNG transparente 1080×1920 com uma faixa (rápido)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([60, H - 360, W - 60, H - 200], fill=(13, 11, 15, 220))  # faixa da legenda
    d.rectangle([W - 380, 150, W - 60, 230], fill=(13, 11, 15, 200))     # pílula do label IA
    img.save(destino)
    return str(destino)


def _gerar_mocks_midia(ff, dir_reel: Path):
    """Cria avatar mp4 + áudio wav (via ffmpeg lavfi) + 2 fotos (Pillow). Sem API."""
    dir_reel.mkdir(parents=True, exist_ok=True)
    avatar = dir_reel / "avatar.mp4"
    _run_ffmpeg(ff, ["-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate=30:duration=2",
                     "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", str(avatar)])
    # narração mock ~= duração do reel (em produção o mp3 do ElevenLabs cobre a fala
    # inteira); assim o -shortest do mux corta no fim do vídeo, com áudio o tempo todo.
    audio = dir_reel / "voz.wav"
    _run_ffmpeg(ff, ["-f", "lavfi", "-i", "sine=frequency=220:duration=40",
                     "-c:a", "pcm_s16le", str(audio)])
    fotos = []
    for i, cor in enumerate([(200, 90, 60), (60, 90, 140)]):
        p = dir_reel / f"foto_{i}.png"
        Image.new("RGB", (1200, 800), cor).save(p)
        fotos.append(str(p))
    return str(avatar), str(audio), fotos


def _info(ff, video: str) -> str:
    import subprocess
    return subprocess.run([ff, "-hide_banner", "-i", video], capture_output=True, text=True).stderr


def _resolucao(ff, video: str) -> tuple[int, int]:
    """Lê a resolução via `ffmpeg -i` (sem ffprobe)."""
    m = re.search(r"(\d{3,4})x(\d{3,4})", _info(ff, video))
    assert m, f"não achei resolução em: {_info(ff, video)[:300]}"
    return int(m.group(1)), int(m.group(2))


def _duracao_s(ff, video: str) -> float:
    """Duração em segundos via `ffmpeg -i` (sem ffprobe)."""
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", _info(ff, video))
    assert m, "não achei Duration"
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def _tem_audio(ff, video: str) -> bool:
    return "Audio:" in _info(ff, video)


def test_montagem_real_ffmpeg():
    ff = _ffmpeg_bin()
    assert ff, "ffmpeg indisponível (PATH ou imageio-ffmpeg)"

    state = escrever_roteiro_video(_base_state(), complete=roteirista_video_fake)
    reel = state["reels_prontos"][0]

    # arquivos que voz.py/avatar.py PRODUZIRIAM com chave — aqui mockados localmente
    avatar, audio, fotos = _gerar_mocks_midia(ff, Path(reel["_dir"]))
    reel["_avatar_video"] = avatar
    reel["_audio"] = audio
    reel["_fotos"] = fotos

    # montagem real via ffmpeg; overlay injetado (Pillow) pra não depender do Chromium
    def montar_real(r, st):
        mp4 = montar_ffmpeg(r, st, ffmpeg=ff, render_overlay=_overlay_fake)
        return (mp4, False) if mp4 else (None, True)

    state = compor_reel(state, montar=montar_real)
    reel = state["reels_prontos"][0]

    # NÃO é placeholder: saiu um MP4 montado
    assert reel["_placeholder"] is False, "deveria ser vídeo real, não placeholder"
    cam = reel["_caminho"]
    assert cam and cam.endswith(".mp4"), f"esperado MP4 montado, veio {cam!r}"
    mp4 = Path(cam)
    assert mp4.exists() and mp4.stat().st_size > 20_000, f"MP4 vazio/pequeno: {mp4.stat().st_size if mp4.exists() else 'inexistente'}"

    # 9:16 1080×1920, com áudio (narração muxada), duração ~= timeline (30-42s)
    assert _resolucao(ff, cam) == (W, H), _resolucao(ff, cam)
    assert _tem_audio(ff, cam), "MP4 final deveria ter faixa de áudio (narração)"
    dur = _duracao_s(ff, cam)
    assert 30 <= dur <= 42, f"duração {dur}s fora do esperado (~38s = soma dos beats)"

    # 5 segmentos (1 por beat) foram gerados e concatenados; 2 fotos viraram b-roll
    assert len(reel.get("_segmentos", [])) == 5, reel.get("_segmentos")
    assert reel.get("_broll_usadas"), "b-roll (fotos) deveria ter sido usado"
    return reel


def main() -> None:
    test_roteiro_video_beats_e_gancho()
    test_voz_pula_sem_chave()
    test_avatar_pula_sem_chave()
    reel = test_pipeline_reel_placeholder()
    print(f"\nreel (sem chaves): placeholder 9:16 + manifest em {Path(reel['_dir']).name}")
    print(f"  placeholder={reel['_placeholder']} · label='{reel['roteiro']['label_ia']}'")

    montado = test_montagem_real_ffmpeg()
    mp4 = Path(montado["_caminho"])
    print(f"\nreel (montagem REAL ffmpeg): {mp4.name} — {mp4.stat().st_size // 1024} KB, 1080×1920")
    print(f"  segmentos: {len(montado['_segmentos'])} (avatar ↔ b-roll) · fotos b-roll: {len(montado['_broll_usadas'])}")
    print("\nREEL OK")


if __name__ == "__main__":
    main()
