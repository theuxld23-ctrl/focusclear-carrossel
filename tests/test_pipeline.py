"""ETAPA 2-6 — PIPELINE COMPLETO do carrossel (pesquisa→PNGs), offline.

Roda com:  python -m tests.test_pipeline   (raiz, venv ativo)
Sucesso = todas as asserções passam, 8 PNGs 1080×1350 gerados e "PIPELINE OK".

Tudo que depende de rede é INJETADO (Brave images, LLM do seletor/roteirista,
download de foto). O COMPOSITOR roda de verdade (Playwright Chromium local, com
fontes embutidas em base64) — os PNGs são reais. Verificamos:
  - validação factual em código descarta time fora da Copa ANTES do LLM;
  - foto com marca de patrocinador é pulada na cascata;
  - 8 PNGs 1080×1350 nascem em engine/output/;
  - a jornada escuro→luz é MENSURÁVEL (luminância sobe do slide 1 ao 8).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageStat  # noqa: E402

import config  # noqa: E402
from engine.nodes.coleta_imagens import coletar_imagens  # noqa: E402
from engine.nodes.seletor import selecionar, validar_factual  # noqa: E402
from engine.nodes.roteirista import escrever_roteiro  # noqa: E402
from engine.nodes.resolve_imagens import (  # noqa: E402
    resolve_imagens,
    risco_patrocinador,
    escolher_candidata,
)
from engine.nodes.compositor import compor, build_html, _headline_html  # noqa: E402


# ── Material pesquisado mockado (saída do nó de pesquisa) ────────────────────
JOGOS = [
    {
        "times": ["Espanha", "Cabo Verde"],
        "placar": "0x0",
        "data": "2026-06-15",
        "fatos_duros": "0x0, estreia do Grupo H, Vozinha (40) com 5 defesas",
        "narrativa": "Aos 40 anos, o goleiro Vozinha segurou a Espanha e garantiu o ponto histórico de Cabo Verde.",
        "fonte": ["brave"],
        "fontes_dados": ["sofascore", "ge", "espn"],
        "fontes_urls": ["https://ge.globo.com/x"],
        "fontes_concordam": True,
    },
    {
        # time FORA da Copa 2026 (Nigéria não está) — deve ser descartado EM CÓDIGO
        "times": ["Nigéria", "Brasil"],
        "placar": "1x2",
        "data": "2026-06-15",
        "narrativa": "jogo que na verdade é de eliminatória, não da Copa",
        "fonte": ["brave"],
        "fontes_urls": ["https://x/y"],
        "fontes_concordam": False,
    },
]

# ── Catálogo de imagens mockado (saída do coleta) ────────────────────────────
IMAGENS_BRAVE = [
    {"properties": {"url": "https://img/cabo-lance.jpg", "width": 1200, "height": 1500},
     "title": "Cabo Verde Vozinha defesa lance jogo", "source": "ge.globo.com"},
    {"properties": {"url": "https://img/torcida.jpg", "width": 1400, "height": 1000},
     "title": "Cabo Verde torcida comemoração estádio", "source": "espn.com.br"},
    # ARMADILHA: photocall com patrocinador — deve ser PULADA
    {"properties": {"url": "https://img/photocall.jpg", "width": 1200, "height": 1500},
     "title": "Vozinha craque do jogo photocall Michelob Ultra", "source": "getty"},
]


def buscar_imagens_fake(query, erros, n=6):
    return IMAGENS_BRAVE


# ── LLM do seletor (fake) ────────────────────────────────────────────────────
def seletor_complete_fake(system, user):
    # prova de que o código filtrou ANTES do LLM: Nigéria não chega ao modelo
    assert "Nig" not in user, "time fora da Copa não pode chegar ao LLM do seletor"
    assert "Cabo Verde" in user
    return json.dumps({
        "pilar": "futebol", "turno": "manha", "data": "2026-06-15", "fase_copa": "grupos",
        "carrosseis_aprovados": [{
            "momento": "Espanha 0x0 Cabo Verde — Vozinha (40) segura a Espanha",
            "validacao_factual": "Espanha e Cabo Verde confirmados na âncora",
            "fatos_confirmados": "Espanha 0x0 Cabo Verde; goleiro Vozinha, 40 anos, 5 defesas",
            "perfil": "ahsd", "razao_do_casamento": "azarão que não era pra estar ali",
            "subgeracao_alvo": "z_ponte", "angulo": None,
            "viabilidade_imagem": "OK", "requer_revisao_medica": False, "prioridade": 1,
        }],
        "descartados": [],
    }, ensure_ascii=False)


# ── LLM do roteirista (fake) — 8 slides na ordem canônica ────────────────────
def _slide(n, funcao, kicker, headline, destaque, sub, busca, **extra):
    s = {"n": n, "funcao": funcao, "kicker": kicker, "headline": headline,
         "palavra_destaque": destaque, "sub": sub,
         "imagem": {"nivel_cascata": 3, "busca": busca, "fallback": "genérica temática"}}
    s.update(extra)
    return s


def roteirista_complete_fake(system, user):
    assert "Cabo Verde" in user and "ahsd" in user
    slides = [
        _slide(1, "gancho", "Copa 2026 · Grupo H", "AOS 40 ANOS\nELE NÃO ERA\nPRA ESTAR ALI",
               "NÃO ERA", "e mesmo assim segurou a Espanha inteira", "Cabo Verde Vozinha defesa"),
        _slide(2, "dado", "o número", "40 ANOS.\n5 DEFESAS.\n1 PONTO.", "1 PONTO",
               "", "Vozinha goleiro Cabo Verde"),
        _slide(3, "espelho", "espelho", "TEM GENTE QUE\nVIVE PROVANDO\nQUE MERECE ESTAR", "PROVANDO",
               "a sensação de que a qualquer hora te mandam embora", "goleiro tenso solidão"),
        _slide(4, "participacao", "e você?", "QUAL DESSES\nÉ VOCÊ HOJE?", None, "",
               "vestiário sozinho introspecção",
               opcoes=["o que segura tudo", "o que se acha pouco", "o que ninguém esperava"]),
        _slide(5, "virada", "vira o jogo", "NÃO É SÓ NO GOL.\nÉ NA VIDA.", "NA VIDA",
               "sentir que não pertence cansa mais que qualquer jogo", "amanhecer estádio leve"),
        _slide(6, "prova", "prova", "O AZARÃO\nAGUENTOU\nATÉ O FIM", "AGUENTOU",
               "e ninguém tirou aquele ponto dele", "Cabo Verde comemoração gramado"),
        _slide(7, "alivio", "isso tem nome", "VOCÊ NÃO ESTÁ\nA MENOS.\nVOCÊ ESTÁ ALI.", "ESTÁ ALI",
               "pertencer não se prova. se ocupa.", "luz suave alívio amanhecer",
               micro_cta_salvar="salva isso pra quando a dúvida voltar"),
        _slide(8, "cta", "FocusClear", "PRA LEMBRAR\nQUE VOCÊ\nMERECE O LUGAR", "MERECE",
               "a gente fala da cabeça por trás do jogo", "amanhecer leve céu"),
    ]
    return "```json\n" + json.dumps({
        "perfil": "ahsd", "subgeracao": "z_ponte", "angulo": None,
        "momento_usado": "Espanha 0x0 Cabo Verde",
        "fatos_base": "Vozinha 40 anos, 5 defesas, 0x0",
        "angulo_rico_encontrado": "o goleiro tem 40 anos — idade que 'não era mais pra estar ali'",
        "slides": slides, "formato_usado": "padrao_8",
        "legenda": "saúde mental também é sobre pertencer: Cabo Verde mostrou isso. ...",
        "utm_sugerida": "copa_ahsd_cabo_verde_v1",
        "checagem_etica": "ok",
    }, ensure_ascii=False) + "\n```"  # cercas markdown de propósito (testa o parser)


def _foto_sintetica() -> bytes:
    """Imagem colorida 1200×1500 (meio-tom) pra o tratamento escuro→luz aparecer."""
    img = Image.new("RGB", (1200, 1500))
    px = img.load()
    for y in range(1500):
        for x in range(0, 1200, 4):  # passo 4 (rápido)
            v = 110 + int(70 * (x / 1200)) - int(30 * (y / 1500))
            for dx in range(4):
                px[x + dx, y] = (v, int(v * 0.7), int(v * 0.55))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def baixar_fake(url):
    return _foto_sintetica()


# ════════════════════════════════════════════════════════════════════════════
# Testes unitários (puros, rápidos)
# ════════════════════════════════════════════════════════════════════════════
def test_validacao_factual_em_codigo():
    validos, descartados = validar_factual(JOGOS)
    assert [j["times"] for j in validos] == [["Espanha", "Cabo Verde"]], validos
    assert len(descartados) == 1 and "fora da Copa" in descartados[0]["motivo"], descartados


def test_risco_patrocinador():
    assert risco_patrocinador({"titulo": "craque do jogo photocall Michelob"}) is True
    assert risco_patrocinador({"titulo": "Cabo Verde lance jogo"}) is False


def test_cascata_pula_patrocinador():
    catalogo = [
        {"url": "a", "titulo": "Vozinha craque do jogo photocall Michelob"},
        {"url": "b", "titulo": "Cabo Verde Vozinha defesa lance jogo"},
    ]
    escolhida = escolher_candidata("Cabo Verde Vozinha defesa", catalogo)
    assert escolhida and escolhida["url"] == "b", escolhida


def test_headline_destaque():
    h = _headline_html("NÃO ERA\nPRA ESTAR", "NÃO ERA")
    assert '<span class="brasa">NÃO ERA</span>' in h
    assert "<br>" in h


# ════════════════════════════════════════════════════════════════════════════
# Pipeline completo → PNGs reais
# ════════════════════════════════════════════════════════════════════════════
def test_pipeline_completo():
    state = {
        "turno": "manha", "pilar_ativo": "futebol", "data": "2026-06-15",
        "fase_copa": "grupos", "jogos_pesquisados": JOGOS, "erros": [],
    }
    state = coletar_imagens(state, buscar_imagens=buscar_imagens_fake)
    assert state["imagens_por_jogo"]["Espanha_x_Cabo Verde"], "catálogo vazio"

    state = selecionar(state, complete=seletor_complete_fake)
    assert len(state["carrosseis_aprovados"]) == 1
    assert any("fora da Copa" in d["motivo"] for d in state["descartados"])
    assert state["carrosseis_aprovados"][0].get("_jogo"), "aprovado deve carregar o jogo"

    state = escrever_roteiro(state, complete=roteirista_complete_fake)
    assert len(state["carrosseis_prontos"]) == 1
    assert len(state["carrosseis_prontos"][0]["slides"]) == 8

    state = resolve_imagens(state, baixar=baixar_fake)
    slides = state["carrosseis_prontos"][0]["slides"]
    assert all(s.get("_bg") for s in slides), "todos os slides deveriam ter bg tratado"

    state = compor(state)  # COMPOSITOR REAL (Playwright)
    pngs = state["carrosseis_prontos"][0]["_pngs"]
    assert len(pngs) == 8, f"esperado 8 PNGs, obtido {len(pngs)}"

    lumis = []
    for p in pngs:
        assert Path(p).exists(), f"PNG não existe: {p}"
        img = Image.open(p)
        assert img.size == (1080, 1350), f"{p} tem {img.size}, esperado (1080,1350)"
        lumis.append(ImageStat.Stat(img.convert("L")).mean[0])

    escuro = sum(lumis[0:3]) / 3   # slides 1-3
    luz = sum(lumis[4:8]) / 4      # slides 5-8
    assert lumis[7] > lumis[0] + 40, f"slide 8 não é mais claro que o 1: {lumis[0]:.0f}->{lumis[7]:.0f}"
    assert luz > escuro + 40, f"jornada escuro→luz fraca: escuro {escuro:.0f} vs luz {luz:.0f}"
    return pngs, lumis, state["carrosseis_prontos"][0]["_dir"]


def main() -> None:
    test_validacao_factual_em_codigo()
    test_risco_patrocinador()
    test_cascata_pula_patrocinador()
    test_headline_destaque()
    pngs, lumis, dir_out = test_pipeline_completo()

    print(f"\npipeline offline: 8 PNGs 1080×1350 em {dir_out}")
    print("luminância por slide (jornada escuro→luz):")
    for i, l in enumerate(lumis, 1):
        barra = "█" * int(l / 6)
        print(f"  slide {i}: {l:6.1f} {barra}")
    print("\nPIPELINE OK")


if __name__ == "__main__":
    main()
