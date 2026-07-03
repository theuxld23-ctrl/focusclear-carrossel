"""Nó 3 — SELETOR (LLM). Decide o que vira carrossel e casa com um perfil.

Princípio #1 (anti-alucinação, dupla camada): a VALIDAÇÃO FACTUAL roda em CÓDIGO
(`validar_factual`) ANTES do LLM. Todo time citado tem que estar na âncora do pilar
(futebol = selecoes_classificadas.json); quem não estiver é descartado sem nunca
chegar ao modelo. Só o que sobrevive é enviado ao LLM (system prompt = seletor.md)
pra o julgamento editorial (carga emocional, casamento de perfil, viabilidade).

Princípio #3: LLM sempre via config.get_llm() — nunca hardcode de provedor.
Costura injetável `complete` permite testar sem rede.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Callable, Optional

from config import DATA, get_llm

_SYSTEM_PROMPT = DATA / "prompts" / "seletor.md"
_SELECOES = DATA / "selecoes_classificadas.json"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def selecoes_validas() -> set[str]:
    """Conjunto normalizado das 48 seleções da Copa (âncora factual do futebol)."""
    d = json.loads(_SELECOES.read_text(encoding="utf-8"))
    nomes: list[str] = []
    for lst in d.get("selecoes_por_confederacao", {}).values():
        if isinstance(lst, list):
            nomes += [x for x in lst if isinstance(x, str)]
    return {_norm(n) for n in nomes}


def validar_factual(
    jogos: list[dict], ancora: Optional[set[str]] = None
) -> tuple[list[dict], list[dict]]:
    """CAMADA DE CÓDIGO. Separa jogos válidos dos descartados por fato.

    Regra: os dois times têm que estar na âncora do pilar. Quem não estiver →
    descartado com motivo "time fora da Copa 2026" (erro real: confundir jogo de
    eliminatória/amistoso — ex. Nigéria, que não está na Copa — com jogo da Copa).
    """
    ancora = ancora if ancora is not None else selecoes_validas()
    validos: list[dict] = []
    descartados: list[dict] = []
    for jogo in jogos:
        times = jogo.get("times") or []
        fora = [t for t in times if _norm(t) not in ancora]
        if len(times) != 2 or fora:
            descartados.append(
                {
                    "momento": " x ".join(times) if times else str(jogo),
                    "motivo": f"time fora da Copa 2026: {', '.join(fora) or 'confronto inválido'}",
                }
            )
        else:
            validos.append(jogo)
    return validos, descartados


def _parse_json(texto: str) -> dict:
    """Extrai o objeto JSON da resposta do LLM (tolera cercas markdown / texto ao redor)."""
    t = texto.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    ini, fim = t.find("{"), t.rfind("}")
    if ini == -1 or fim == -1:
        raise ValueError(f"resposta do LLM sem JSON: {texto[:200]!r}")
    return json.loads(t[ini : fim + 1])


def _resumo_imagens(state: dict, jogo: dict) -> dict:
    from engine.nodes.coleta_imagens import jogo_key

    imgs = (state.get("imagens_por_jogo") or {}).get(jogo_key(jogo), [])
    return {"quantidade": len(imgs), "amostra_titulos": [i.get("titulo", "") for i in imgs[:3]]}


def _payload_usuario(state: dict, validos: list[dict]) -> str:
    material = []
    for j in validos:
        material.append(
            {
                "times": j.get("times"),
                "placar": j.get("placar"),
                "narrativa": j.get("narrativa", ""),
                "fatos_duros": j.get("fatos_duros", ""),
                "fontes_concordam": j.get("fontes_concordam"),
                "imagens": _resumo_imagens(state, j),
            }
        )
    payload = {
        "pilar_ativo": state.get("pilar_ativo", "futebol"),
        "turno": state.get("turno", "manha"),
        "data": state.get("data", ""),
        "fase_copa": state.get("fase_copa", ""),
        "material_pesquisado": material,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _casa_jogo(momento: str, fatos: str, validos: list[dict]) -> Optional[dict]:
    """Liga um carrossel aprovado de volta ao jogo pesquisado (por nome de time)."""
    alvo = _norm(f"{momento} {fatos}")
    for j in validos:
        times = j.get("times") or []
        if times and all(_norm(t) in alvo for t in times):
            return j
    return None


def selecionar(
    state: dict,
    complete: Optional[Callable[[str, str], str]] = None,
) -> dict:
    """Valida em código, chama o LLM e devolve carrosseis_aprovados + descartados."""
    complete = complete or get_llm()
    jogos = state.get("jogos_pesquisados", [])

    # CAMADA 1 (código): validação factual anti-alucinação.
    validos, descartados_fato = validar_factual(jogos)

    if not validos:
        state["carrosseis_aprovados"] = []
        state["descartados"] = descartados_fato
        return state

    # CAMADA 2 (LLM): julgamento editorial.
    system = _SYSTEM_PROMPT.read_text(encoding="utf-8")
    saida = _parse_json(complete(system, _payload_usuario(state, validos)))

    aprovados = saida.get("carrosseis_aprovados", []) or []
    for a in aprovados:
        jogo = _casa_jogo(a.get("momento", ""), a.get("fatos_confirmados", ""), validos)
        if jogo is not None:
            a["_jogo"] = jogo  # carrega placar/narrativa/imagens pro roteirista

    state["carrosseis_aprovados"] = aprovados
    state["descartados"] = descartados_fato + (saida.get("descartados", []) or [])
    return state
