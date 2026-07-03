"""FASE 3 — pipeline de REEL (roteiro falado → voz → avatar → montagem), offline.

Roda com:  python -m tests.test_reel   (raiz, venv ativo)
Sucesso = asserções passam, gera output placeholder e imprime "REEL OK".

Tudo que depende de chave é INJETADO/pulado:
  - roteirista_video: LLM fake com os 5 beats;
  - voz (ElevenLabs) e avatar (HeyGen): chaves vazias → PULAM com placeholder;
  - reel_compositor: gera poster 9:16 + manifest sempre; o vídeo webm placeholder
    (Chromium, sem ffmpeg) é exercitado num teste à parte.
Label "conteúdo gerado por IA" presente no manifest e no plano.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from engine.nodes.roteirista_video import escrever_roteiro_video, checar_roteiro  # noqa: E402
from engine.nodes.voz import gerar_voz  # noqa: E402
from engine.nodes.avatar import gerar_avatar  # noqa: E402
from engine.nodes.reel_compositor import compor_reel  # noqa: E402

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


def main() -> None:
    test_roteiro_video_beats_e_gancho()
    test_voz_pula_sem_chave()
    test_avatar_pula_sem_chave()
    reel = test_pipeline_reel_placeholder()
    print(f"\nreel offline: poster 9:16 + manifest em {Path(reel['_dir']).name}")
    print(f"  placeholder={reel['_placeholder']} · label='{reel['roteiro']['label_ia']}'")
    print("\nREEL OK")


if __name__ == "__main__":
    main()
