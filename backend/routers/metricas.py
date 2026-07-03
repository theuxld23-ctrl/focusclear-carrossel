"""Endpoints de métricas — ESTRUTURA pronta para a Instagram Graph API (v2).

Hoje a tabela `metricas` fica vazia (sem Graph API conectada). `GET /metricas`
devolve o que houver + um resumo (médias) quando há linhas, ou resumo nulo quando
vazio. A aba /metricas mostra os números reais quando existirem e um estado vazio
claro enquanto não. Nenhuma chamada externa acontece aqui."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db, Metrica

router = APIRouter(prefix="/metricas", tags=["metricas"])


def _media(valores: list) -> Optional[float]:
    nums = [v for v in valores if v is not None]
    return round(sum(nums) / len(nums), 1) if nums else None


def _soma(valores: list) -> Optional[int]:
    nums = [v for v in valores if v is not None]
    return sum(nums) if nums else None


def resumo_metricas(rows: list) -> Optional[dict]:
    """Agrega as linhas em cards de topo (puro, testável). None se não há dados.

    swipe_rate/completion = médias (%); saves/shares = somas (contagem)."""
    if not rows:
        return None
    return {
        "swipe_rate": _media([r.swipe_rate for r in rows]),
        "saves": _soma([r.saves for r in rows]),
        "shares": _soma([r.shares for r in rows]),
        "completion": _media([r.completion for r in rows]),
        "n_posts": len(rows),
    }


@router.get("/")
def listar_metricas(
    workspace_id: str = "focusclear",
    periodo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Metrica).filter_by(workspace_id=workspace_id)
    if periodo:
        q = q.filter(Metrica.periodo == periodo)
    linhas = q.order_by(Metrica.coletado_em.desc()).limit(200).all()
    return {
        "metricas": linhas,
        "resumo": resumo_metricas(linhas),
        "fonte": "instagram_graph_api",  # rótulo do que popula (v2)
        "conectada": False,  # vira True quando a Graph API estiver ligada
    }
