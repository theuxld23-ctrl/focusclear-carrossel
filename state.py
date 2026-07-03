"""Estado do pipeline (LangGraph).

CarrosselState atravessa os 7 nós: pesquisa -> coleta_imagens -> seletor ->
roteirista -> resolve_imagens -> compositor -> telegram.
total=False: cada nó preenche apenas os campos que produz.
"""
from __future__ import annotations

from typing import Any, TypedDict


class CarrosselState(TypedDict, total=False):
    pilar_ativo: str                 # pilar da execução (default "futebol"); ver engine/data/pilares.json
    pilar_config: dict[str, Any]     # entrada do pilar ativo, carregada de pilares.json no início do fluxo
    turno: str                       # "manha" | "tarde"
    data: str                        # data de execução (YYYY-MM-DD)
    data_alvo: str                   # dia dos jogos pesquisados (ontem, p/ manhã)
    fase_copa: str                   # fase atual do calendário da Copa
    jogos_pesquisados: list[dict[str, Any]]
    imagens_por_jogo: dict[str, Any]
    carrosseis_aprovados: list[dict[str, Any]]
    descartados: list[dict[str, Any]]
    carrosseis_prontos: list[dict[str, Any]]
    erros: list[str]
    plano_b_acionado: bool
