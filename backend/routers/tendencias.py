"""Endpoints de tendências — listar (vazio até a Brave API popular)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db, Tendencia

router = APIRouter(prefix="/tendencias", tags=["tendencias"])


@router.get("/")
def listar_tendencias(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return (
        db.query(Tendencia)
        .filter_by(workspace_id=workspace_id)
        .order_by(Tendencia.score.desc(), Tendencia.data.desc())
        .limit(100)
        .all()
    )
