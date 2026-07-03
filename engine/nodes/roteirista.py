"""Nó 4 — ROTEIRISTA (LLM). Escreve os 8 slides (jornada escuro→luz).

Para cada carrossel aprovado, monta o payload (briefing + FATOS CONFIRMADOS do
jogo + dados do perfil/subgeração) e chama o LLM com system prompt = roteirista.md.
O modelo NUNCA inventa fato — só escreve sobre os fatos confirmados que recebe.

Cada slide declara a cascata de imagem (nivel_cascata/busca/fallback) que o
resolve_imagens vai executar. Limites de texto são checados em código (soft) e
anexados como avisos — a Lei anti-genérico exige headline lida em 1 segundo.

Princípio #3: LLM via config.get_llm(). Costura injetável `complete` p/ teste.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Callable, Optional

from config import DATA, get_llm
from engine.nodes.coleta_imagens import jogo_key

_SYSTEM_PROMPT = DATA / "prompts" / "roteirista.md"
_PONTE = DATA / "ponte_emocional.json"
_MATRIZ = DATA / "matriz_subgeracao.json"

# Limites duros de palavras por função (do roteirista.md) — checagem em código.
_LIMITE_HEADLINE = {"gancho": 10, "dado": 12, "espelho": 12, "virada": 12, "prova": 12, "alivio": 12}
_FUNCOES_8 = ["gancho", "dado", "espelho", "participacao", "virada", "prova", "alivio", "cta"]
_FUNCOES_6 = ["gancho", "espelho", "participacao", "virada", "alivio", "cta"]


def _perfil(nome: str) -> dict:
    d = json.loads(_PONTE.read_text(encoding="utf-8"))
    return d.get(nome, {})


def _subgeracoes() -> dict:
    d = json.loads(_MATRIZ.read_text(encoding="utf-8"))
    subs = d.get("subgeracoes", {})
    return subs if isinstance(subs, dict) else {}


def _parse_json(texto: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    ini, fim = t.find("{"), t.rfind("}")
    if ini == -1 or fim == -1:
        raise ValueError(f"resposta do LLM sem JSON: {texto[:200]!r}")
    return json.loads(t[ini : fim + 1])


def _payload_usuario(state: dict, aprovado: dict) -> str:
    perfil_nome = aprovado.get("perfil", "")
    perfil = _perfil(perfil_nome)
    subg_nome = aprovado.get("subgeracao_alvo", "z_ponte")
    subg = _subgeracoes().get(subg_nome, {})

    jogo = aprovado.get("_jogo", {})
    imgs = (state.get("imagens_por_jogo") or {}).get(jogo_key(jogo), []) if jogo else []

    payload = {
        "briefing": {
            "momento": aprovado.get("momento"),
            "perfil": perfil_nome,
            "subgeracao": subg_nome,
            "angulo": aprovado.get("angulo"),
            "requer_revisao_medica": aprovado.get("requer_revisao_medica", False),
            "viabilidade_imagem": aprovado.get("viabilidade_imagem"),
        },
        "fatos_confirmados": {
            "descricao": aprovado.get("fatos_confirmados", ""),
            "times": jogo.get("times"),
            "placar": jogo.get("placar"),
            "narrativa": jogo.get("narrativa", ""),
        },
        "dados_perfil": {
            "emocao_nucleo": perfil.get("emocao_nucleo"),
            "experiencia_em_linguagem_popular": perfil.get("experiencia_em_linguagem_popular"),
            "linha_alivio_o_premio": perfil.get("linha_alivio_o_premio"),
            "cta_emocional": perfil.get("cta_emocional"),
            "restricoes_eticas": perfil.get("restricoes_eticas"),
        },
        "dados_subgeracao": subg,
        "imagens_disponiveis": [
            {"titulo": i.get("titulo", ""), "fonte": i.get("fonte", "")} for i in imgs
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _conta_palavras(txt: str) -> int:
    return len((txt or "").replace("\n", " ").split())


def checar_limites(roteiro: dict) -> list[str]:
    """Avisos (soft) de headline acima do limite — não falha, sinaliza."""
    avisos: list[str] = []
    for s in roteiro.get("slides", []):
        func = s.get("funcao", "")
        lim = _LIMITE_HEADLINE.get(func)
        if lim:
            n = _conta_palavras(s.get("headline", ""))
            if n > lim:
                avisos.append(f"slide {s.get('n')} ({func}): headline com {n} palavras > {lim}")
    return avisos


def escrever_roteiro(
    state: dict,
    complete: Optional[Callable[[str, str], str]] = None,
) -> dict:
    """Gera um roteiro de 8 (ou 6) slides por carrossel aprovado."""
    complete = complete or get_llm()
    system = _SYSTEM_PROMPT.read_text(encoding="utf-8")
    erros = state.setdefault("erros", [])

    prontos: list[dict] = []
    for aprovado in state.get("carrosseis_aprovados", []):
        try:
            roteiro = _parse_json(complete(system, _payload_usuario(state, aprovado)))
        except Exception as e:  # noqa: BLE001 — um carrossel falho não derruba os outros
            erros.append(f"roteirista falhou p/ {aprovado.get('momento')!r}: {e!r}")
            continue

        slides = roteiro.get("slides", [])
        n = len(slides)
        if n not in (6, 8):
            erros.append(f"roteiro com {n} slides (esperado 6 ou 8): {aprovado.get('momento')!r}")
        roteiro["_perfil"] = aprovado.get("perfil")
        roteiro["_jogo"] = aprovado.get("_jogo", {})
        roteiro["_avisos_limite"] = checar_limites(roteiro)
        prontos.append(roteiro)

    state["carrosseis_prontos"] = prontos
    return state
