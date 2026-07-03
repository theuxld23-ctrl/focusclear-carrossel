"""Nó 2 — COLETA DE IMAGENS. Cataloga fotos por jogo/momento via Brave Image Search.

Não escolhe nem trata nada aqui — só monta o CATÁLOGO de candidatas por jogo,
que o roteirista consulta (pra saber viabilidade visual) e o resolve_imagens
percorre na cascata (estrategia_imagem.md). Fonte = Brave (mesma da pesquisa).

Costura injetável `buscar_imagens` permite testar sem rede.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import requests

from config import require_brave_key

_BRAVE_IMAGES = "https://api.search.brave.com/res/v1/images/search"
_TIMEOUT = 12


def jogo_key(jogo: dict) -> str:
    """Chave estável do jogo/momento no catálogo (times na ordem do jogo)."""
    t = jogo.get("times") or ["?", "?"]
    return f"{t[0]}_x_{t[1]}"


def _brave_images(query: str, erros: list[str], n: int = 8) -> list[dict]:
    """Resultados crus da Brave Image Search. Levanta erro claro se sem chave."""
    key = require_brave_key()
    r = requests.get(
        _BRAVE_IMAGES,
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": n, "country": "br", "search_lang": "pt"},
        timeout=_TIMEOUT,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Brave Images HTTP {r.status_code} (q={query!r})")
    return r.json().get("results", []) or []


def _normalizar(res: dict) -> Optional[dict]:
    """Extrai o essencial de um resultado de imagem do Brave."""
    props = res.get("properties") or {}
    url = props.get("url") or res.get("url")
    if not url:
        return None
    return {
        "url": url,
        "titulo": res.get("title", ""),
        "fonte": res.get("source", ""),
        "w": int(props.get("width") or 0),
        "h": int(props.get("height") or 0),
        "thumb": (res.get("thumbnail") or {}).get("src", ""),
    }


def _queries_do_jogo(jogo: dict) -> list[str]:
    """Queries de imagem por jogo/momento: lance/protagonista + reação/contexto."""
    t = jogo.get("times") or []
    if len(t) == 2:
        base = f"{t[0]} x {t[1]} Copa do Mundo 2026"
        return [
            f"{base} lance jogo",
            f"{base} torcida comemoração",
            f"{t[0]} {t[1]} estádio",
        ]
    # Pilar não-futebol: sem times, usa o momento (entidade extraída) como base.
    momento = (jogo.get("momento") or jogo.get("fatos_duros") or "").strip()
    return [f"{momento} foto", f"{momento} repercussão"] if momento else ["assunto do dia foto"]


def coletar_imagens(
    state: dict,
    buscar_imagens: Optional[Callable[[str, list[str], int], list[dict]]] = None,
) -> dict:
    """Para cada jogo pesquisado, cataloga imagens candidatas em state['imagens_por_jogo'].

    Estrutura: { jogo_key: [ {url, titulo, fonte, w, h, thumb}, ... ] }.
    Um jogo sem imagem não derruba o resto (registra em erros).
    """
    buscar = buscar_imagens or _brave_images
    erros = state.setdefault("erros", [])
    catalogo: dict[str, list[dict]] = {}

    for jogo in state.get("jogos_pesquisados", []):
        chave = jogo_key(jogo)
        encontradas: list[dict] = []
        vistos: set[str] = set()
        for q in _queries_do_jogo(jogo):
            try:
                for res in buscar(q, erros, 6):
                    item = _normalizar(res)
                    if item and item["url"] not in vistos:
                        vistos.add(item["url"])
                        encontradas.append(item)
            except Exception as e:  # noqa: BLE001 — falha de uma query não derruba o jogo
                erros.append(f"imagens {chave} q={q!r} falhou: {e!r}")
        catalogo[chave] = encontradas
        if not encontradas:
            erros.append(f"nenhuma imagem catalogada para {chave}")

    state["imagens_por_jogo"] = catalogo
    return state
