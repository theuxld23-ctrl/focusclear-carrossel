"""FASE 5+ — PILARES NÃO-FUTEBOL PONTA A PONTA (âncora por consenso), offline.

Roda com:  python -m tests.test_pilares
Sucesso = asserções passam, 8 PNGs 1080×1350 gerados e imprime "PILARES OK".

Prova que um pilar NÃO-futebol (cultura_pop) roda o pipeline INTEIRO usando as
QUERIES e a ÂNCORA POR CONSENSO do próprio pilar, sem rede/LLM real:

  pesquisa_pilar (Brave mockado, conta fontes distintas por entidade)
    → validar_factual (consenso ≥2 fontes substitui a lista fixa do futebol)
    → selecionar (LLM mockado)
    → escrever_roteiro (LLM mockado, 8 slides — método idêntico ao do futebol)
    → resolve_imagens (download mockado)
    → compor (COMPOSITOR REAL, Playwright) → 8 PNGs reais 1080×1350.

Anti-alucinação sem lista: uma entidade citada por UMA fonte única é DESCARTADA;
só o que várias fontes contam igual (consenso) sobrevive. Isso é o que substitui a
`selecoes_classificadas.json` nos pilares que não podem ter lista fixa.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageStat  # noqa: E402

from config import DATA  # noqa: E402
from engine.nodes.pesquisa import pesquisa_pilar, queries_do_pilar  # noqa: E402
from engine.nodes.coleta_imagens import coletar_imagens  # noqa: E402
from engine.nodes.seletor import validar_factual, selecionar  # noqa: E402
from engine.nodes.roteirista import escrever_roteiro  # noqa: E402
from engine.nodes.resolve_imagens import resolve_imagens  # noqa: E402
from engine.nodes.compositor import compor  # noqa: E402

# ── Snippets crus mockados de "cultura pop" (Brave web results) ──────────────
# ÂNCORA POR CONSENSO em ação: "Fulano de Tal" e "Aqueles Caras" são confirmados
# por várias fontes distintas (metropoles/uol/g1) → passam. "Ricardo Sozinho"
# aparece só num blog obscuro (fonte única) → RUÍDO, é descartado (anti-alucinação).
CULTURA = [
    {"title": "Polêmica: influencer Fulano de Tal detona canal Aqueles Caras",
     "description": "A treta entre Fulano de Tal e Aqueles Caras dominou as redes hoje.",
     "url": "https://www.metropoles.com/entretenimento/a"},
    {"title": "Fulano de Tal rebate críticas e vira alvo de julgamento público",
     "description": "Aqueles Caras respondeu e a briga virou o assunto do dia.",
     "url": "https://www.uol.com.br/splash/b"},
    {"title": "Web reage à exposição de Fulano de Tal",
     "description": "Repercussão da confusão tomou conta das redes sociais.",
     "url": "https://gshow.globo.com/pop-arte/c"},
    # RUÍDO: entidade citada por UMA fonte única e obscura → sem consenso → descartada.
    {"title": "Ricardo Sozinho aparece em post isolado",
     "description": "Boato não confirmado circula apenas num blog pequeno.",
     "url": "https://www.blogaleatorio.example/d"},
]

_QUERIES_VISTAS: list[str] = []


def buscar_fake(query: str):
    _QUERIES_VISTAS.append(query)
    return CULTURA


# ── Catálogo de imagens mockado (cultura pop — títulos neutros, sem patrocínio) ─
IMAGENS_CP = [
    {"properties": {"url": "https://img/cp-pensativa.jpg", "width": 1200, "height": 1500},
     "title": "pessoa pensativa olhando celular rede social", "source": "unsplash"},
    {"properties": {"url": "https://img/cp-grupo.jpg", "width": 1400, "height": 1000},
     "title": "grupo de amigos conversa mesa cafe", "source": "unsplash"},
    {"properties": {"url": "https://img/cp-luz.jpg", "width": 1200, "height": 1500},
     "title": "amanhecer janela luz suave calma", "source": "unsplash"},
]


def buscar_imagens_fake(query, erros, n=6):
    return IMAGENS_CP


# ── LLM do seletor (fake): aprova 1 carrossel casando com o momento de consenso ─
def complete_fake(system: str, user: str) -> str:
    payload = json.loads(user)
    assert payload["pilar_ativo"] == "cultura_pop", payload["pilar_ativo"]
    momentos = [m.get("momento") for m in payload["material_pesquisado"] if m.get("momento")]
    assert momentos, "seletor deveria receber momentos (não jogos de futebol)"
    # o seletor NUNCA recebe a entidade de fonte única (o código já descartou)
    assert not any("Ricardo Sozinho" in (m or "") for m in momentos), \
        "entidade sem consenso não pode chegar ao LLM do seletor"
    alvo = momentos[0]
    return json.dumps({
        "pilar": "cultura_pop", "turno": "manha",
        "carrosseis_aprovados": [{
            "momento": alvo,
            "validacao_factual": f"{alvo} confirmado por múltiplas fontes (consenso)",
            "fatos_confirmados": f"{alvo} repercutiu hoje nas redes",
            "perfil": "ansiedade",
            "razao_do_casamento": "medo de ser julgado/excluído do grupo",
            "subgeracao_alvo": "z_ponte", "angulo": None,
            "viabilidade_imagem": "OK", "requer_revisao_medica": False, "prioridade": 1,
        }],
        "descartados": [],
    }, ensure_ascii=False)


# ── LLM do roteirista (fake): 8 slides cultura pop — MÉTODO idêntico ao futebol ─
# gancho cultural → virada emocional → alívio. Cuidado ético: fala da EMOÇÃO que o
# público projeta, nunca ataca a pessoa real (o nome não vira alvo, vira contexto).
def _slide(n, funcao, kicker, headline, destaque, sub, busca, **extra):
    s = {"n": n, "funcao": funcao, "kicker": kicker, "headline": headline,
         "palavra_destaque": destaque, "sub": sub,
         "imagem": {"nivel_cascata": 3, "busca": busca, "fallback": "genérica temática"}}
    s.update(extra)
    return s


def roteirista_cp_fake(system: str, user: str) -> str:
    payload = json.loads(user)
    assert payload["briefing"]["perfil"] == "ansiedade", payload["briefing"]["perfil"]
    slides = [
        _slide(1, "gancho", "cultura pop · hoje", "JULGARAM ELE\nSEM SABER\nA HISTÓRIA", "SEM SABER",
               "a internet inteira formou opinião em minutos", "pessoa pensativa celular"),
        _slide(2, "dado", "o número", "7 EM 10\nJÁ SE SENTIRAM\nEXPOSTOS ASSIM", "EXPOSTOS",
               "", "celular tela julgamento"),
        _slide(3, "espelho", "espelho", "O MEDO DE\nSER O PRÓXIMO\nA SOBRAR", "SOBRAR",
               "aquela sensação de que um erro te tira do grupo", "solidao grupo margem"),
        _slide(4, "participacao", "e você?", "COMO VOCÊ\nLIDA COM ISSO?", None, "",
               "pessoa sozinha reflexão",
               opcoes=["evito me expor", "travo com medo", "finjo que não ligo"]),
        _slide(5, "virada", "vira a chave", "NÃO É SOBRE ELE.\nÉ SOBRE VOCÊ.", "VOCÊ",
               "o julgamento lá fora ecoa o que você teme por dentro", "amanhecer janela leve"),
        _slide(6, "prova", "prova", "PERTENCER NÃO\nSE PROVA\nO TEMPO TODO", "PERTENCER",
               "quem te quer bem não te cobra plateia", "grupo amigos acolhimento"),
        _slide(7, "alivio", "isso tem nome", "VOCÊ NÃO ESTÁ\nEM JULGAMENTO.\nVOCÊ ESTÁ AQUI.", "AQUI",
               "ansiedade social tem nome — e tem saída", "luz suave calma manhã",
               micro_cta_salvar="salva isso pra quando o medo do julgamento voltar"),
        _slide(8, "cta", "FocusClear", "PRA LEMBRAR\nQUE VOCÊ\nJÁ BASTA", "JÁ BASTA",
               "a gente fala da cabeça por trás do barulho", "amanhecer leve céu aberto"),
    ]
    return "```json\n" + json.dumps({
        "perfil": "ansiedade", "subgeracao": "z_ponte", "angulo": None,
        "momento_usado": payload["briefing"]["momento"],
        "fatos_base": "repercussão de hoje nas redes",
        "angulo_rico_encontrado": "julgamento público → medo de ser excluído",
        "slides": slides, "formato_usado": "padrao_8",
        "legenda": "ansiedade social: quando o julgamento de fora vira medo por dentro. ...",
        "utm_sugerida": "cultura_pop_ansiedade_v1",
        "checagem_etica": "fala da emoção projetada; não ataca a pessoa real",
    }, ensure_ascii=False) + "\n```"


def _foto_sintetica() -> bytes:
    """Imagem 1200×1500 meio-tom pra o tratamento escuro→luz aparecer nos PNGs."""
    img = Image.new("RGB", (1200, 1500))
    px = img.load()
    for y in range(1500):
        for x in range(0, 1200, 4):
            v = 110 + int(70 * (x / 1200)) - int(30 * (y / 1500))
            for dx in range(4):
                px[x + dx, y] = (v, int(v * 0.7), int(v * 0.55))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def baixar_fake(url):
    return _foto_sintetica()


# ════════════════════════════════════════════════════════════════════════════
# 1. QUERIES e PESQUISA por pilar
# ════════════════════════════════════════════════════════════════════════════
def test_queries_do_pilar():
    qs = queries_do_pilar("cultura_pop")
    assert qs and any("polêmica" in q.lower() or "bbb" in q.lower() for q in qs), qs
    # pilar desconhecido → deriva do config (carga_emocional)
    qd = queries_do_pilar("novo_pilar", {"carga_emocional": "saudade, recomeço"})
    assert any("saudade" in q.lower() for q in qd), qd


def test_pesquisa_pilar_usa_queries_do_pilar():
    _QUERIES_VISTAS.clear()
    state = {"pilar_ativo": "cultura_pop", "pilar_config": {}, "erros": []}
    state = pesquisa_pilar(state, buscar=buscar_fake)
    # usou as queries de cultura pop (não as de futebol/Copa)
    assert _QUERIES_VISTAS and all("copa" not in q.lower() for q in _QUERIES_VISTAS), _QUERIES_VISTAS
    momentos = state["jogos_pesquisados"]
    assert momentos, "deveria extrair momentos dos snippets"
    # momentos não têm times (não é futebol) mas têm entidade + narrativa
    assert all(m["times"] == [] for m in momentos), momentos
    termos = " | ".join(m["momento"].lower() for m in momentos)
    assert "fulano de tal" in termos or "aqueles caras" in termos, termos
    # cada momento carrega a contagem de consenso (âncora anti-alucinação)
    assert all("n_fontes" in m and "fontes_concordam" in m for m in momentos), momentos
    return state


def test_pesquisa_pilar_conta_consenso():
    """A entidade multi-fonte tem consenso; a de fonte única, não."""
    state = {"pilar_ativo": "cultura_pop", "pilar_config": {}, "erros": []}
    state = pesquisa_pilar(state, buscar=buscar_fake)
    por_nome = {m["momento"]: m for m in state["jogos_pesquisados"]}
    fulano = next((v for k, v in por_nome.items() if "Fulano de Tal" in k), None)
    ruido = next((v for k, v in por_nome.items() if "Ricardo Sozinho" in k), None)
    assert fulano and fulano["n_fontes"] >= 2 and fulano["fontes_concordam"] is True, fulano
    assert ruido and ruido["n_fontes"] == 1 and ruido["fontes_concordam"] is False, ruido
    # confirmado por fontes DISTINTAS (metropoles/uol/gshow), não por repetição
    assert len(fulano["fontes_dados"]) == fulano["n_fontes"], fulano


# ════════════════════════════════════════════════════════════════════════════
# 2. VALIDAÇÃO FACTUAL por consenso (substitui a lista fixa)
# ════════════════════════════════════════════════════════════════════════════
def test_validar_factual_consenso():
    momentos = [
        {"times": [], "momento": "Fulano de Tal", "n_fontes": 3, "fontes_concordam": True},
        {"times": [], "momento": "Aqueles Caras", "fontes_dados": ["metropoles", "uol"]},  # 2 domínios
        {"times": [], "momento": "Ricardo Sozinho", "n_fontes": 1, "fontes_concordam": False},  # ruído
        {"times": [], "momento": ""},  # vazio
    ]
    validos, descartados = validar_factual(momentos, pilar="cultura_pop")
    nomes_ok = {v["momento"] for v in validos}
    assert nomes_ok == {"Fulano de Tal", "Aqueles Caras"}, nomes_ok
    motivos = " | ".join(d["motivo"] for d in descartados)
    assert "consenso" in motivos and "Ricardo Sozinho" in {d["momento"] for d in descartados}, descartados
    # futebol continua exigindo os 2 times na âncora (lista fixa intocada)
    fut_validos, _ = validar_factual([{"times": ["Nárnia", "Atlantis"]}], pilar="futebol")
    assert fut_validos == [], "time fora da Copa deve ser descartado no futebol"


# ════════════════════════════════════════════════════════════════════════════
# 3. PROMPTS conscientes de pilar (âncora por consenso + cuidado ético)
# ════════════════════════════════════════════════════════════════════════════
def test_prompts_conscientes_de_pilar():
    seletor_md = (DATA / "prompts" / "seletor.md").read_text(encoding="utf-8").lower()
    roteirista_md = (DATA / "prompts" / "roteirista.md").read_text(encoding="utf-8").lower()
    # seletor: âncora por consenso documentada + exemplos por pilar
    assert "consenso" in seletor_md and "n_fontes" in seletor_md, "seletor.md sem âncora por consenso"
    assert "julgamento público" in seletor_md or "julgamento publico" in seletor_md, seletor_md[:0]
    assert "música" in seletor_md and "natal" in seletor_md, "seletor.md sem exemplos música/datas"
    # roteirista: método cross-pilar + cuidado ético OBRIGATÓRIO de cultura pop
    assert "método" in roteirista_md or "metodo" in roteirista_md, "roteirista.md sem nota de método"
    assert "cuidado ético" in roteirista_md or "cuidado etico" in roteirista_md, \
        "roteirista.md sem bloco de cuidado ético"
    assert "não atacar" in roteirista_md or "nao atacar" in roteirista_md \
        or "pessoa real" in roteirista_md, "roteirista.md não proíbe atacar a pessoa real"


# ════════════════════════════════════════════════════════════════════════════
# 4. SELETOR pilar-aware (cultura pop)
# ════════════════════════════════════════════════════════════════════════════
def test_selecionar_pilar_cultura_pop():
    state = test_pesquisa_pilar_usa_queries_do_pilar()
    state = selecionar(state, complete=complete_fake)
    aprovados = state["carrosseis_aprovados"]
    assert aprovados, "seletor deveria aprovar 1 carrossel de cultura_pop"
    # o momento aprovado foi religado ao material pesquisado (narrativa preservada)
    assert aprovados[0].get("_jogo", {}).get("narrativa"), aprovados[0]
    return state


# ════════════════════════════════════════════════════════════════════════════
# 5. E2E — carrossel cultura pop até 8 PNGs REAIS (compositor Playwright)
# ════════════════════════════════════════════════════════════════════════════
def test_carrossel_cultura_pop_e2e():
    state = {
        "pilar_ativo": "cultura_pop", "pilar_config": {}, "turno": "manha",
        "data": "2026-07-03", "fase_copa": "", "erros": [],
    }
    state = pesquisa_pilar(state, buscar=buscar_fake)
    # o ruído de fonte única NÃO sobrevive à âncora por consenso
    validos, descartados = validar_factual(state["jogos_pesquisados"], pilar="cultura_pop")
    assert any("Ricardo Sozinho" in d["momento"] for d in descartados), descartados

    state = coletar_imagens(state, buscar_imagens=buscar_imagens_fake)
    assert state["imagens_por_jogo"].get("?_x_?"), "catálogo do momento (sem times) vazio"

    state = selecionar(state, complete=complete_fake)
    assert len(state["carrosseis_aprovados"]) == 1
    assert state["carrosseis_aprovados"][0].get("_jogo"), "aprovado deve carregar o momento"

    state = escrever_roteiro(state, complete=roteirista_cp_fake)
    assert len(state["carrosseis_prontos"]) == 1
    slides = state["carrosseis_prontos"][0]["slides"]
    assert len(slides) == 8, f"esperado 8 slides, obtido {len(slides)}"

    state = resolve_imagens(state, baixar=baixar_fake)
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

    escuro = sum(lumis[0:3]) / 3
    luz = sum(lumis[4:8]) / 4
    assert lumis[7] > lumis[0] + 40, f"slide 8 não é mais claro que o 1: {lumis[0]:.0f}->{lumis[7]:.0f}"
    assert luz > escuro + 40, f"jornada escuro→luz fraca: escuro {escuro:.0f} vs luz {luz:.0f}"
    return pngs, lumis, state["carrosseis_prontos"][0]["_dir"]


def main() -> None:
    test_queries_do_pilar()
    test_pesquisa_pilar_usa_queries_do_pilar()
    test_pesquisa_pilar_conta_consenso()
    test_validar_factual_consenso()
    test_prompts_conscientes_de_pilar()
    state = test_selecionar_pilar_cultura_pop()
    ap = state["carrosseis_aprovados"][0]

    print("\npilar cultura_pop (mock) — âncora por consenso:")
    print(f"  queries usadas: {_QUERIES_VISTAS}")
    print(f"  momento aprovado: {ap['momento']!r} · perfil={ap['perfil']}")
    print(f"  fontes que confirmam: {ap['_jogo'].get('fontes_dados')} "
          f"(consenso={ap['_jogo'].get('fontes_concordam')})")

    pngs, lumis, dir_out = test_carrossel_cultura_pop_e2e()
    print(f"\ncarrossel cultura_pop offline: 8 PNGs 1080×1350 em {dir_out}")
    print("luminância por slide (jornada escuro→luz):")
    for i, l in enumerate(lumis, 1):
        barra = "█" * int(l / 6)
        print(f"  slide {i}: {l:6.1f} {barra}")
    print("\nPILARES OK")


if __name__ == "__main__":
    main()
