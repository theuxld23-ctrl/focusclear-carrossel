"""Nó — ROTEIRISTA DE VÍDEO (LLM). Roteiro FALADO de Reel (30-45s, 9:16).

Deriva do roteirista.md (mesmo método espelho, mesma anti-alucinação) mas escreve
para a FALA de um avatar, não para slides. Beats (briefing 4B):
  0-3s gancho (≤14 palavras) → tensão → espelho → virada+alívio → CTA+loop.
Total 70-110 palavras. Cada beat traz indicação de B-ROLL (foto real do momento).

Princípio #3: LLM via config.get_llm(). Costura injetável `complete` p/ teste.
Não toca nos nós de carrossel — consome carrosseis_aprovados do seletor.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Callable, Optional

from config import DATA, OUTPUT, get_llm

_ROTEIRISTA_MD = DATA / "prompts" / "roteirista.md"
_PONTE = DATA / "ponte_emocional.json"

# Adendo que transforma o roteirista de slides em roteirista de FALA (Reel).
_ADENDO_VIDEO = """

═══════════════════════════════════════════════════════════════════════════
ADENDO — MODO VÍDEO (REEL 9:16, 30-45s)
═══════════════════════════════════════════════════════════════════════════
Agora você NÃO escreve slides. Escreve a FALA de um avatar talking-head do
FocusClear (voz fictícia da marca). Mesmo método espelho, mesma anti-alucinação.

REGRAS DO REEL:
- 70 a 110 palavras no total (30-45s falados).
- Fala natural, primeira pessoa coletiva ("a gente"), zero jargão clínico.
- BEATS obrigatórios, nesta ordem:
  1. gancho   — 0-3s, ATÉ 14 palavras. Para o scroll. Domínio do pilar (futebol).
  2. tensao   — aprofunda o gancho, cria a dúvida.
  3. espelho  — nomeia a experiência/dor humana (a virada começa).
  4. virada_alivio — ponte futebol→mente + a linha de alívio (o prêmio).
  5. cta_loop — CTA suave ("segue @focusclear") + frase que amarra de volta ao gancho (loop).
- Cada beat: um B-ROLL (que foto real do momento aparece enquanto se fala aquilo).
- Legendas existem desde o frame 1 (o compositor cuida; você só escreve a fala).
- NUNCA invente fato — use só os FATOS CONFIRMADOS.

SAÍDA — JSON estrito, nada antes/depois:
{
  "momento_usado": "...", "perfil": "...", "subgeracao": "...",
  "texto_completo": "a fala inteira, corrida",
  "duracao_estimada_s": 38,
  "beats": [
    {"beat": "gancho", "texto": "...", "b_roll": "que foto aparece", "palavras": 0},
    {"beat": "tensao", "texto": "...", "b_roll": "..."},
    {"beat": "espelho", "texto": "...", "b_roll": "..."},
    {"beat": "virada_alivio", "texto": "...", "b_roll": "..."},
    {"beat": "cta_loop", "texto": "...", "b_roll": "..."}
  ],
  "label_ia": "conteúdo gerado por IA",
  "checagem_etica": "confirma restrições; se trauma: REQUER_REVISAO_MEDICA"
}
Inclua "palavras" no beat gancho como auto-verificação (≤14). Se passar, REESCREVA.
"""

_BEATS_ESPERADOS = ["gancho", "tensao", "espelho", "virada_alivio", "cta_loop"]


def _perfil(nome: str) -> dict:
    d = json.loads(_PONTE.read_text(encoding="utf-8"))
    return d.get(nome, {})


def _parse_json(texto: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    ini, fim = t.find("{"), t.rfind("}")
    if ini == -1 or fim == -1:
        raise ValueError(f"resposta do LLM sem JSON: {texto[:200]!r}")
    return json.loads(t[ini : fim + 1])


def _system_prompt() -> str:
    return _ROTEIRISTA_MD.read_text(encoding="utf-8") + _ADENDO_VIDEO


def _payload_usuario(aprovado: dict) -> str:
    perfil_nome = aprovado.get("perfil", "")
    perfil = _perfil(perfil_nome)
    jogo = aprovado.get("_jogo", {})
    payload = {
        "briefing": {
            "momento": aprovado.get("momento"),
            "perfil": perfil_nome,
            "subgeracao": aprovado.get("subgeracao_alvo", "z_ponte"),
            "angulo": aprovado.get("angulo"),
            "requer_revisao_medica": aprovado.get("requer_revisao_medica", False),
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
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "reel"


def _dir_reel(state: dict, reel: dict, i: int) -> str:
    times = "-".join((reel.get("_jogo", {}) or {}).get("times", []) or ["reel"])
    nome = _slug(f"reel-{state.get('data','')}-{reel.get('_perfil','')}-{times}-{i}")
    return str(OUTPUT / nome)


def _conta_palavras(txt: str) -> int:
    return len((txt or "").split())


def checar_roteiro(roteiro: dict) -> list[str]:
    """Avisos soft: total de palavras (70-110) e gancho (≤14)."""
    avisos: list[str] = []
    total = _conta_palavras(roteiro.get("texto_completo", ""))
    if not (60 <= total <= 120):
        avisos.append(f"texto com {total} palavras (alvo 70-110)")
    for b in roteiro.get("beats", []):
        if b.get("beat") == "gancho" and _conta_palavras(b.get("texto", "")) > 14:
            avisos.append(f"gancho com {_conta_palavras(b.get('texto',''))} palavras > 14")
    return avisos


def escrever_roteiro_video(
    state: dict,
    complete: Optional[Callable[[str, str], str]] = None,
) -> dict:
    """Gera um roteiro falado (reel) por momento aprovado pelo seletor."""
    complete = complete or get_llm()
    system = _system_prompt()
    erros = state.setdefault("erros", [])

    reels: list[dict] = []
    for i, aprovado in enumerate(state.get("carrosseis_aprovados", [])):
        try:
            roteiro = _parse_json(complete(system, _payload_usuario(aprovado)))
        except Exception as e:  # noqa: BLE001 — um reel falho não derruba os outros
            erros.append(f"roteirista_video falhou p/ {aprovado.get('momento')!r}: {e!r}")
            continue
        roteiro.setdefault("label_ia", "conteúdo gerado por IA")
        reel = {
            "momento": aprovado.get("momento"),
            "_perfil": aprovado.get("perfil"),
            "_jogo": aprovado.get("_jogo", {}),
            "roteiro": roteiro,
            "_avisos": checar_roteiro(roteiro),
        }
        reel["_dir"] = _dir_reel(state, reel, i)
        reels.append(reel)

    state["reels_prontos"] = reels
    return state
