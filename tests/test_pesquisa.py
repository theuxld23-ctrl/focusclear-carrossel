"""ETAPA 1 — nó de PESQUISA (fonte = Brave; anti-alucinação).

Roda com:  python -m tests.test_pesquisa   (a partir da raiz, com o venv ativo)
Sucesso = todas as asserções passam e imprime "ETAPA 1 OK".

A Brave é a única fonte (SofaScore/FotMob bloqueiam o IP do VPS). O teste injeta
payloads BRUTOS REAIS de resultados da Brave Web Search para 2026-06-15
(Espanha 0x0 Cabo Verde) e valida que o normalizador extrai os fatos certos a
partir de SNIPPETS — com consenso entre fontes e sem inventar. Roda sem rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from engine.nodes.pesquisa import (  # noqa: E402
    derivar_fase,
    pesquisa_manha,
    pesquisa_tarde,
    _extrair_fato_jogo,
    _extrair_narrativa,
    _extrair_confrontos,
    _placar_no_texto,
)

DATA_ALVO = "2026-06-15"  # rodada 1 da fase de grupos (grupo H)

# Resultados crus da Brave Web Search p/ "Espanha x Cabo Verde resultado Copa 2026".
# 3 fontes confiáveis concordam em 0x0; 1 blog NÃO-confiável traz placar errado
# (deve ser ignorado).
FATOS_ESPANHA_CV = [
    {
        "title": "Espanha 0 x 0 Cabo Verde - Resumo - 15/06/2026 | SofaScore",
        "description": "Acompanhe Espanha 0 x 0 Cabo Verde pela Copa do Mundo 2026. Estatísticas, escalações e lances.",
        "url": "https://www.sofascore.com/espanha-cabo-verde/abc123",
    },
    {
        "title": "Cabo Verde segura empate histórico com a Espanha",
        "description": "Estreante na Copa, Cabo Verde arrancou um 0 a 0 contra a Espanha em Atlanta.",
        "url": "https://ge.globo.com/futebol/copa-do-mundo/noticia/2026/06/15/espanha-cabo-verde.ghtml",
    },
    {
        "title": "Espanha tropeça e fica no 0 x 0 com Cabo Verde",
        "description": "A Espanha não saiu do 0 x 0 diante de Cabo Verde na estreia do Grupo H.",
        "url": "https://www.espn.com.br/futebol/copa-do-mundo/artigo/espanha-cabo-verde",
    },
    {
        # FONTE NÃO-CONFIÁVEL com placar errado — tem que ser ignorada
        "title": "Espanha goleia Cabo Verde por 3 x 0, diz blog",
        "description": "Espanha 3 x 0 Cabo Verde segundo o palpiteiro do blog.",
        "url": "https://blogdopalpite.example.com/espanha-cabo-verde",
    },
]

# Narrativa: "Cabo Verde Copa 2026" (protagonista).
NARR_CABO_VERDE = [
    {
        "title": "Vozinha, o goleiro de 40 anos que parou a Espanha",
        "description": "Aos 40 anos, o goleiro Vozinha fez defesas decisivas e garantiu o ponto histórico de Cabo Verde.",
        "url": "https://www.cnnbrasil.com.br/esportes/cabo-verde-vozinha",
    },
    {
        "title": "A festa de Cabo Verde na estreia em Copas",
        "description": "Menor país a disputar uma Copa, Cabo Verde celebrou o empate como uma vitória.",
        "url": "https://ge.globo.com/futebol/copa-do-mundo/cabo-verde-estreia.ghtml",
    },
]

# Descoberta de confrontos: snippets de "resultados Copa 15 de junho".
DESCOBERTA_15 = [
    {
        "title": "Resultados da Copa em 15/06: Espanha 0 x 0 Cabo Verde e mais",
        "description": "Confira: Espanha 0 x 0 Cabo Verde, Arábia Saudita 1 x 2 Uruguai pelo Grupo H.",
        "url": "https://ge.globo.com/futebol/copa-do-mundo/resultados-15-06.ghtml",
    },
]


def test_placar_no_texto():
    assert _placar_no_texto("Espanha 0 x 0 Cabo Verde", "Espanha", "Cabo Verde") == "0x0"
    # ordem invertida no texto -> normaliza para a ordem (t1, t2)
    assert _placar_no_texto("Cabo Verde 2 x 1 Espanha", "Espanha", "Cabo Verde") == "1x2"
    assert _placar_no_texto("empatou em 0 a 0", "Espanha", "Cabo Verde") is None  # sem nomes
    assert _placar_no_texto("Arábia Saudita 1-2 Uruguai", "Arábia Saudita", "Uruguai") == "1x2"


def test_extrai_fato_com_consenso():
    j = _extrair_fato_jogo(["Espanha", "Cabo Verde"], FATOS_ESPANHA_CV)
    assert j["placar"] == "0x0", f"placar errado: {j['placar']!r}"
    assert j["fontes_concordam"] is True, "3 fontes confiáveis deveriam concordar"
    # blog não-confiável (3x0) ignorado e fora das fontes
    assert set(j["fontes_dados"]) == {"sofascore", "ge", "espn"}, j["fontes_dados"]
    assert all("blogdopalpite" not in u for u in j["fontes_urls"]), "blog não pode ser fonte"
    assert j["fontes_urls"], "deve registrar URLs (rastreabilidade)"
    assert j["fonte"] == ["brave"]


def test_conflito_deixa_placar_vazio():
    """Duas fontes confiáveis discordam, sem maioria -> placar None (dúvida, não chuta)."""
    conflito = [
        {"title": "Espanha 0 x 0 Cabo Verde", "description": "", "url": "https://sofascore.com/x"},
        {"title": "Espanha 1 x 0 Cabo Verde", "description": "", "url": "https://espn.com.br/y"},
    ]
    j = _extrair_fato_jogo(["Espanha", "Cabo Verde"], conflito)
    assert j["placar"] is None, "conflito sem maioria deve deixar placar vazio"
    assert j["fontes_concordam"] is False


def test_fonte_unica_marca_nao_concordam():
    unica = [{"title": "Espanha 0 x 0 Cabo Verde", "description": "", "url": "https://sofascore.com/x"}]
    j = _extrair_fato_jogo(["Espanha", "Cabo Verde"], unica)
    assert j["placar"] == "0x0"
    assert j["fontes_concordam"] is False, "fonte única não é consenso"


def test_descobre_confrontos():
    pares = _extrair_confrontos(DESCOBERTA_15)
    assert ["Espanha", "Cabo Verde"] in pares, pares
    assert ["Arábia Saudita", "Uruguai"] in pares, pares


def test_pesquisa_manha():
    def descobrir_fake(data_iso, erros):
        return [["Espanha", "Cabo Verde"]]

    def buscar_jogo_fake(times, data_iso, erros):
        j = _extrair_fato_jogo(times, FATOS_ESPANHA_CV)
        j["data"] = data_iso
        j["narrativa"] = _extrair_narrativa(NARR_CABO_VERDE)
        return j

    state = {"turno": "manha", "data_alvo": DATA_ALVO}
    state = pesquisa_manha(state, descobrir=descobrir_fake, buscar_jogo=buscar_jogo_fake)

    jogos = state["jogos_pesquisados"]
    assert len(jogos) >= 1, "deve retornar ao menos 1 jogo"
    assert state["fase_copa"] == "grupos", f"fase errada: {state['fase_copa']!r}"

    for j in jogos:
        assert isinstance(j["times"], list) and len(j["times"]) == 2, j
        assert j["data"], f"data vazia: {j}"
        assert j["fatos_duros"] or j["narrativa"], f"jogo sem fato nem narrativa: {j}"
        assert j["fonte"] and j["fontes_urls"], f"sem rastreabilidade: {j}"

    cv = jogos[0]
    assert cv["placar"] == "0x0" and cv["fontes_concordam"] is True
    assert "Vozinha" in cv["narrativa"], "narrativa do Brave deveria ter sido extraída"
    return jogos


def test_um_jogo_falho_nao_derruba():
    def descobrir_fake(data_iso, erros):
        return [["Espanha", "Cabo Verde"], ["Arábia Saudita", "Uruguai"]]

    def buscar_jogo_fake(times, data_iso, erros):
        if "Uruguai" in times:
            raise RuntimeError("timeout simulado")
        j = _extrair_fato_jogo(times, FATOS_ESPANHA_CV)
        j["data"] = data_iso
        return j

    state = pesquisa_manha({"data_alvo": DATA_ALVO}, descobrir=descobrir_fake, buscar_jogo=buscar_jogo_fake)
    assert len(state["jogos_pesquisados"]) == 1, "jogo bom deve sobreviver à falha do outro"
    assert any("timeout simulado" in e for e in state["erros"]), "erro do jogo falho deve constar"


def test_brave_key_ausente_falha_claro():
    """Sem BRAVE_API_KEY -> erro legível, não exceção crua de HTTP."""
    salvo = config.BRAVE_API_KEY
    config.BRAVE_API_KEY = ""
    import os
    salvo_env = os.environ.pop("BRAVE_API_KEY", None)
    try:
        try:
            config.require_brave_key()
            assert False, "deveria ter levantado RuntimeError"
        except RuntimeError as e:
            assert "BRAVE_API_KEY não configurada" in str(e), str(e)
    finally:
        config.BRAVE_API_KEY = salvo
        if salvo_env is not None:
            os.environ["BRAVE_API_KEY"] = salvo_env


def test_pesquisa_tarde():
    def hist_fake(tema, erros):
        return {
            "times": list(tema["times"]),
            "placar": None,
            "data": "",
            "fatos_duros": "",
            "narrativa": f"história de {tema['times'][0]} x {tema['times'][1]}",
            "fonte": ["brave"],
            "fontes_dados": ["ge"],
            "fontes_urls": ["https://ge.globo.com/x"],
            "fontes_concordam": False,
        }

    state = pesquisa_tarde({"turno": "tarde"}, buscar_hist=hist_fake, n=2)
    momentos = state["jogos_pesquisados"]
    assert len(momentos) == 2, f"tarde deve produzir 2, obtido {len(momentos)}"
    for m in momentos:
        assert len(m["times"]) == 2 and m["narrativa"] and m["fonte"]


def main() -> None:
    test_placar_no_texto()
    test_extrai_fato_com_consenso()
    test_conflito_deixa_placar_vazio()
    test_fonte_unica_marca_nao_concordam()
    test_descobre_confrontos()
    jogos = test_pesquisa_manha()
    test_um_jogo_falho_nao_derruba()
    test_brave_key_ausente_falha_claro()
    test_pesquisa_tarde()

    print(f"\nfonte: Brave (única). fase derivada p/ {DATA_ALVO}: grupos")
    print(f"jogos extraídos dos snippets ({len(jogos)}):")
    for j in jogos:
        placar = j["placar"] or "—"
        ok = "✓ consenso" if j["fontes_concordam"] else "⚠ rever"
        print(f"  • {j['times'][0]} {placar} {j['times'][1]}  [{ok}; fontes: {','.join(j['fontes_dados'])}]")
        print(f"    narrativa: {j['narrativa'][:90]}...")
        print(f"    urls: {len(j['fontes_urls'])} registradas")

    print("\nETAPA 1 OK")


if __name__ == "__main__":
    main()
