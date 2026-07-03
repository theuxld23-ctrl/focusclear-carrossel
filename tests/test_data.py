"""ETAPA 0 — validação dos dados (fonte de verdade).

Roda com:  python -m tests.test_data   (a partir da raiz do projeto)
Sucesso = todas as asserções passam e imprime "ETAPA 0 OK".

Extração ajustada ao formato real dos arquivos em engine/data/:
- ponte_emocional.json: dict com perfis em chaves de topo (+ metadados _doc/_angulos_transversais)
- selecoes_classificadas.json: 48 seleções em selecoes_por_confederacao (espelhadas em grupos A–L)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# raiz do projeto na frente do sys.path para `import config` ao rodar via -m
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA  # noqa: E402

PERFIS_ESPERADOS = {"ansiedade", "burnout", "trauma", "hiperfoco", "ahsd"}
SELECOES_PROIBIDAS = {"Itália", "Nigéria", "Chile"}
TOTAL_SELECOES = 48
PILARES_ESPERADOS = {"futebol", "novela_reality", "musica_popular", "datas_sazonais"}


def _load(name: str):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def _perfis(ponte: dict) -> dict:
    """Perfis = chaves de topo, exceto metadados prefixados com '_'."""
    return {k: v for k, v in ponte.items() if not k.startswith("_")}


def _nomes_selecoes(selecoes: dict) -> list[str]:
    """48 seleções = união das listas de selecoes_por_confederacao."""
    conf = selecoes["selecoes_por_confederacao"]
    nomes: list[str] = []
    for lista in conf.values():
        if isinstance(lista, list):
            nomes.extend(lista)
    return nomes


def _find_nested(obj, key: str):
    """Busca recursiva pela primeira ocorrência de `key` em dicts aninhados."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_nested(v, key)
            if r is not None:
                return r
    return None


def main() -> None:
    # 1. os JSONs parseiam
    ponte = _load("ponte_emocional.json")
    selecoes = _load("selecoes_classificadas.json")
    _matriz = _load("matriz_subgeracao.json")
    _calendario = _load("calendario_copa.json")
    pilares = _load("pilares.json")

    # 2. ponte_emocional tem exatamente os 5 perfis
    perfis = _perfis(ponte)
    nomes_perfis = set(perfis.keys())
    assert nomes_perfis == PERFIS_ESPERADOS, (
        f"perfis esperados {PERFIS_ESPERADOS}, obtidos {nomes_perfis}"
    )

    # 2b. cada perfil tem criterio_de_casamento (genérico) com exemplos de futebol preservados
    for nome, p in perfis.items():
        crit = p.get("criterio_de_casamento")
        assert isinstance(crit, dict), f"{nome}: falta criterio_de_casamento (genérico)"
        assert "criterio_de_casamento_futebol" not in p, (
            f"{nome}: criterio_de_casamento_futebol devia ter sido generalizado"
        )
        assert crit.get("a_dor"), f"{nome}: criterio_de_casamento.a_dor ausente"
        exemplos = crit.get("exemplos_por_pilar") or {}
        assert exemplos.get("futebol"), (
            f"{nome}: exemplos_por_pilar.futebol ausente (inteligência de futebol perdida)"
        )

    # 2c. pilares.json: parseia, tem os 4 pilares, futebol=ativo (único ativo, prioridade 1)
    plr = pilares.get("pilares") or {}
    assert set(plr.keys()) == PILARES_ESPERADOS, (
        f"pilares esperados {PILARES_ESPERADOS}, obtidos {set(plr.keys())}"
    )
    assert plr["futebol"].get("status") == "ativo", (
        f"pilar futebol deve estar 'ativo', obtido {plr['futebol'].get('status')!r}"
    )
    ativos = {pid for pid, p in plr.items() if p.get("status") == "ativo"}
    assert ativos == {"futebol"}, f"v1: só futebol ativo, obtidos {ativos}"
    assert plr["futebol"].get("prioridade") == 1, "futebol deve ter prioridade 1"
    assert "rotacao" in pilares, "pilares.json deve ter bloco 'rotacao'"
    for pid, pconf in plr.items():
        for campo in ("status", "prioridade", "ancora_factual", "fontes_pesquisa",
                      "tipo_momento", "carga_emocional", "cuidado"):
            assert campo in pconf, f"pilar {pid}: campo '{campo}' ausente"

    # 3. selecoes: 48, sem duplicatas, sem Itália/Nigéria/Chile (âncora anti-alucinação)
    nomes_sel = _nomes_selecoes(selecoes)
    assert len(nomes_sel) == TOTAL_SELECOES, (
        f"esperado {TOTAL_SELECOES} seleções, obtido {len(nomes_sel)}"
    )
    assert len(set(nomes_sel)) == TOTAL_SELECOES, "há seleções duplicadas"
    assert selecoes.get("total") == TOTAL_SELECOES, (
        f"campo 'total' deveria ser {TOTAL_SELECOES}, obtido {selecoes.get('total')}"
    )
    presentes_proibidas = {n for n in nomes_sel if n in SELECOES_PROIBIDAS}
    assert not presentes_proibidas, (
        f"seleções proibidas presentes na lista de classificadas: {presentes_proibidas}"
    )

    # 4. trauma tem nivel_cuidado contendo ALTO (aninhado em restricoes_eticas)
    nivel = str(_find_nested(perfis["trauma"], "nivel_cuidado") or "")
    assert "ALTO" in nivel, (
        f"trauma.nivel_cuidado deve conter 'ALTO', obtido {nivel!r}"
    )

    # 5. prompts existem
    assert (DATA / "prompts" / "seletor.md").exists(), "prompts/seletor.md ausente"
    assert (DATA / "prompts" / "roteirista.md").exists(), "prompts/roteirista.md ausente"

    print("ETAPA 0 OK")


if __name__ == "__main__":
    main()
