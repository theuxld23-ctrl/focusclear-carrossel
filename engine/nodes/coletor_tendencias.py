"""Coletor de TENDÊNCIAS por pilar (Brave). Roda 1x/dia via APScheduler.

Para cada pilar ATIVO monta queries de recência, extrai entidades/momentos dos
snippets da Brave, pontua por frequência + recência + fonte confiável, e devolve
as top tendências (o scheduler persiste na tabela `tendencias`).

Sem BRAVE_API_KEY → PULA em silêncio (log, sem erro). Costura injetável
`buscar(query) -> list[snippets]` permite testar sem rede.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Optional

import requests

import config

_BRAVE_WEB = "https://api.search.brave.com/res/v1/web/search"

# Queries de recência por pilar (slug de pilares.json). Fallback genérico abaixo.
_QUERIES_POR_PILAR: dict[str, list[str]] = {
    "futebol": [
        "Copa do Mundo 2026 destaque hoje",
        "resultado jogo Copa do Mundo hoje repercussão",
    ],
    "cultura_pop": [
        "polêmica influencer hoje Brasil",
        "treta canal YouTube repercussão hoje",
        "BBB assunto do dia hoje",
    ],
    "musica_popular": [
        "música viral hoje Brasil sertanejo funk pagode",
        "lançamento música repercussão hoje",
    ],
    "datas_sazonais": [
        "data comemorativa próxima Brasil em alta",
        "campanha sazonal assunto do momento",
    ],
}

# Fontes confiáveis dão bônus de score (reaproveita a lógica de consenso do projeto).
_FONTES_CONFIAVEIS = (
    "globo.com", "uol.com.br", "g1.globo", "gshow", "cnnbrasil", "espn",
    "lance", "cazetv", "youtube.com", "metropoles", "terra.com.br",
)

# Ruído a descartar como termo (genérico demais pra ser tendência).
_STOP = {
    "brasil", "hoje", "veja", "confira", "assista", "saiba", "vídeo", "video",
    "notícias", "noticias", "ao vivo", "copa", "mundo", "the", "com",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _brave(query: str, key: str, n: int = 10) -> list[dict]:
    r = requests.get(
        _BRAVE_WEB,
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": n, "country": "br", "search_lang": "pt", "freshness": "pd"},
        timeout=12,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Brave HTTP {r.status_code} (q={query!r})")
    return (r.json().get("web") or {}).get("results", []) or []


_CONECTORES = {"de", "da", "do", "dos", "das", "e", "no", "na"}


def extrair_candidatos(texto: str) -> list[str]:
    """Extrai entidades: sequências de palavras Capitalizadas (com conectores)."""
    tokens = re.findall(r"[\wÀ-ÿ]+", texto or "")
    frases: list[str] = []
    buf: list[str] = []
    for t in tokens:
        if t[:1].isupper() and len(t) > 2:
            buf.append(t)
        elif buf and t.lower() in _CONECTORES:
            buf.append(t.lower())
        else:
            if buf:
                frases.append(" ".join(buf))
            buf = []
    if buf:
        frases.append(" ".join(buf))

    limpas: list[str] = []
    for f in frases:
        f = f.strip()
        while f and f.split()[-1].lower() in _CONECTORES:
            f = " ".join(f.split()[:-1])
        pals = f.split()
        if not pals:
            continue
        # aceita: 2+ palavras, ou 1 palavra "forte" (>=4 letras, não-stop)
        if len(pals) >= 2 or (len(pals) == 1 and len(pals[0]) >= 4 and _norm(pals[0]) not in _STOP):
            if _norm(f) not in _STOP:
                limpas.append(f)
    return limpas


def _fonte_confiavel(url: str) -> bool:
    u = _norm(url)
    return any(f in u for f in _FONTES_CONFIAVEIS)


def coletar_tendencias(
    pilares: list[str],
    buscar: Optional[Callable[[str], list[dict]]] = None,
    brave_key: Optional[str] = None,
    por_pilar: int = 6,
) -> list[dict]:
    """Retorna [{pilar, termo, score}] das top tendências por pilar. [] se sem chave."""
    key = brave_key if brave_key is not None else config.BRAVE_API_KEY
    if not buscar and not key:
        print("[tendencias] BRAVE_API_KEY ausente — pulando coleta")
        return []
    buscar = buscar or (lambda q: _brave(q, key))

    saida: list[dict] = []
    for pilar in pilares:
        queries = _QUERIES_POR_PILAR.get(pilar, [f"{pilar} assunto em alta hoje Brasil"])
        agrega: dict[str, dict[str, Any]] = {}  # termo_norm -> {termo, ocorr, fontes, recencia}
        for q in queries:
            try:
                snippets = buscar(q)
            except Exception as e:  # noqa: BLE001 — uma query falha não derruba o pilar
                print(f"[tendencias] pilar={pilar} query={q!r} falhou: {e!r}")
                continue
            for s in snippets:
                texto = f"{s.get('title','')} {s.get('description','')}"
                recente = any(w in _norm(texto) for w in ("hoje", "agora", "nesta", "acaba de"))
                conf = _fonte_confiavel(s.get("url", ""))
                for cand in extrair_candidatos(texto):
                    chave = _norm(cand)
                    d = agrega.setdefault(chave, {"termo": cand, "ocorr": 0, "fontes": 0, "recencia": 0})
                    d["ocorr"] += 1
                    d["fontes"] += 1 if conf else 0
                    d["recencia"] += 1 if recente else 0

        ranqueadas = sorted(
            agrega.values(),
            key=lambda d: d["ocorr"] * 10 + d["fontes"] * 5 + d["recencia"] * 3,
            reverse=True,
        )
        for d in ranqueadas[:por_pilar]:
            score = d["ocorr"] * 10 + d["fontes"] * 5 + d["recencia"] * 3
            saida.append({"pilar": pilar, "termo": d["termo"], "score": int(score)})

    return saida
