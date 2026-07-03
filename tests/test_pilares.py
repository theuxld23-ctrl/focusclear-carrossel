"""FASE 5 (parte 1) — PILARES FUNCIONAIS (pesquisa por pilar + seletor), offline.

Roda com:  python -m tests.test_pilares
Sucesso = asserções passam e imprime "PILARES OK".

Prova que um pilar NÃO-futebol (cultura_pop) roda o começo do pipeline usando as
QUERIES do próprio pilar: pesquisa_pilar (Brave mockado) → validar_factual
(pilar-aware, sem âncora de futebol) → selecionar (LLM mockado). Sem rede/LLM real.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json  # noqa: E402

from engine.nodes.pesquisa import pesquisa_pilar, queries_do_pilar  # noqa: E402
from engine.nodes.seletor import validar_factual, selecionar  # noqa: E402

# Snippets crus mockados de "cultura pop" (Brave web results).
CULTURA = [
    {"title": "Polêmica: influencer Fulano de Tal detona canal Aqueles Caras",
     "description": "A treta entre Fulano de Tal e Aqueles Caras dominou o Twitter hoje.",
     "url": "https://www.metropoles.com/entretenimento/a"},
    {"title": "Fulano de Tal rebate críticas hoje",
     "description": "Aqueles Caras respondeu e a briga virou assunto do dia.",
     "url": "https://www.uol.com.br/splash/b"},
]

_QUERIES_VISTAS: list[str] = []


def buscar_fake(query: str):
    _QUERIES_VISTAS.append(query)
    return CULTURA


def complete_fake(system: str, user: str) -> str:
    """LLM mockado: devolve 1 carrossel aprovado casando com o momento pesquisado."""
    payload = json.loads(user)
    assert payload["pilar_ativo"] == "cultura_pop", payload["pilar_ativo"]
    momentos = [m.get("momento") for m in payload["material_pesquisado"] if m.get("momento")]
    assert momentos, "seletor deveria receber momentos (não jogos de futebol)"
    alvo = momentos[0]
    return json.dumps({
        "carrosseis_aprovados": [{
            "momento": alvo,
            "perfil": "ansiedade",
            "subgeracao_alvo": "z_ponte",
            "angulo": "medo de ser excluído do grupo",
            "fatos_confirmados": f"{alvo} repercutiu hoje",
        }],
        "descartados": [],
    })


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
    return state


def test_validar_factual_pilar_aware():
    momentos = [{"times": [], "momento": "Fulano de Tal"}, {"times": [], "momento": ""}]
    validos, descartados = validar_factual(momentos, pilar="cultura_pop")
    assert len(validos) == 1 and validos[0]["momento"] == "Fulano de Tal"
    assert len(descartados) == 1  # o vazio cai
    # futebol continua exigindo os 2 times na âncora
    fut_validos, _ = validar_factual([{"times": ["Nárnia", "Atlantis"]}], pilar="futebol")
    assert fut_validos == [], "time fora da Copa deve ser descartado no futebol"


def test_selecionar_pilar_cultura_pop():
    state = test_pesquisa_pilar_usa_queries_do_pilar()
    state = selecionar(state, complete=complete_fake)
    aprovados = state["carrosseis_aprovados"]
    assert aprovados, "seletor deveria aprovar 1 carrossel de cultura_pop"
    # o momento aprovado foi religado ao material pesquisado (narrativa preservada)
    assert aprovados[0].get("_jogo", {}).get("narrativa"), aprovados[0]
    return state


def main() -> None:
    test_queries_do_pilar()
    test_pesquisa_pilar_usa_queries_do_pilar()
    test_validar_factual_pilar_aware()
    state = test_selecionar_pilar_cultura_pop()
    ap = state["carrosseis_aprovados"][0]
    print("\npilar cultura_pop (mock):")
    print(f"  queries usadas: {_QUERIES_VISTAS}")
    print(f"  momento aprovado: {ap['momento']!r} · perfil={ap['perfil']}")
    print(f"  narrativa religada: {ap['_jogo']['narrativa'][:60]!r}")
    print("\nPILARES OK")


if __name__ == "__main__":
    main()
