"""FASE 4 (parte 1) — COLETOR DE TENDÊNCIAS (Brave), offline.

Roda com:  python -m tests.test_tendencias
Sucesso = asserções passam e imprime "TENDENCIAS OK".

Injeta payloads BRUTOS da Brave (sem rede). Verifica extração de entidades,
pontuação (frequência + fonte confiável + recência) e o skip sem chave.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.nodes.coletor_tendencias import (  # noqa: E402
    coletar_tendencias,
    extrair_candidatos,
)

# Snippets crus mockados por query (Brave web results).
BRAVE_FUTEBOL = [
    {"title": "Cabo Verde surpreende e segura a Espanha na estreia",
     "description": "Vozinha, goleiro de Cabo Verde, brilhou hoje contra a Espanha na Copa do Mundo.",
     "url": "https://ge.globo.com/futebol/copa-do-mundo/x.ghtml"},
    {"title": "Vozinha vira herói de Cabo Verde",
     "description": "Aos 40 anos, Vozinha fez defesas decisivas hoje. Cabo Verde comemora.",
     "url": "https://www.espn.com.br/futebol/y"},
    {"title": "Blog de palpites fala do jogo",
     "description": "Espanha e Cabo Verde empataram.",
     "url": "https://blogaleatorio.example.com/z"},
]

CULTURA = [
    {"title": "Polêmica: influencer Fulano de Tal detona canal Aqueles Caras",
     "description": "A treta entre Fulano de Tal e Aqueles Caras dominou o Twitter hoje.",
     "url": "https://www.metropoles.com/entretenimento/a"},
]


def buscar_fake(query):
    q = query.lower()
    if "copa" in q or "jogo" in q:
        return BRAVE_FUTEBOL
    return CULTURA


def test_extrair_candidatos():
    cands = extrair_candidatos("Vozinha, goleiro de Cabo Verde, brilhou contra a Espanha")
    norm = [c.lower() for c in cands]
    assert any("cabo verde" in c for c in norm), cands
    assert any("vozinha" in c for c in norm), cands
    assert any("espanha" in c for c in norm), cands


def test_coleta_pontua_e_ranqueia():
    tends = coletar_tendencias(["futebol", "cultura_pop"], buscar=buscar_fake, por_pilar=5)
    assert tends, "deveria coletar tendências"
    por_pilar = {}
    for t in tends:
        assert t["score"] > 0 and isinstance(t["score"], int)
        por_pilar.setdefault(t["pilar"], []).append(t["termo"].lower())

    # futebol: Cabo Verde e Vozinha aparecem em 2 fontes confiáveis + "hoje"
    fut = " | ".join(por_pilar.get("futebol", []))
    assert "cabo verde" in fut and "vozinha" in fut, por_pilar.get("futebol")
    # cultura_pop coletado por queries próprias
    assert "cultura_pop" in por_pilar, por_pilar

    # ranking: o termo top do futebol tem score >= os demais
    fut_scores = [t["score"] for t in tends if t["pilar"] == "futebol"]
    assert fut_scores == sorted(fut_scores, reverse=True), "deve vir ranqueado desc"


def test_pula_sem_chave():
    tends = coletar_tendencias(["futebol"], brave_key="")  # sem buscar e sem chave
    assert tends == [], "sem BRAVE_API_KEY deve pular e retornar []"


def main() -> None:
    test_extrair_candidatos()
    test_coleta_pontua_e_ranqueia()
    test_pula_sem_chave()
    tends = coletar_tendencias(["futebol", "cultura_pop"], buscar=buscar_fake, por_pilar=4)
    print("\ntendências coletadas (mock):")
    for t in tends:
        print(f"  [{t['pilar']}] {t['termo']} — score {t['score']}")
    print("\nTENDENCIAS OK")


if __name__ == "__main__":
    main()
