"""Endpoints de pilares — listar e editar (status + config)."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db, Pilar

router = APIRouter(prefix="/pilares", tags=["pilares"])


@router.get("/")
def listar_pilares(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    pilares = db.query(Pilar).filter_by(workspace_id=workspace_id).all()
    # ordena por prioridade (config.prioridade), pilares sem prioridade ao fim
    return sorted(pilares, key=lambda p: (p.config or {}).get("prioridade") or 99)


class PatchPilar(BaseModel):
    status: Optional[str] = None  # ativo | planejado | desativado
    config: Optional[dict[str, Any]] = None


@router.patch("/{pilar_id}")
def atualizar_pilar(pilar_id: int, patch: PatchPilar, db: Session = Depends(get_db)):
    pilar = db.query(Pilar).filter_by(id=pilar_id).first()
    if not pilar:
        raise HTTPException(404, "Pilar não encontrado")
    if patch.status is not None:
        if patch.status not in ("ativo", "planejado", "desativado"):
            raise HTTPException(422, "status inválido")
        pilar.status = patch.status
    if patch.config is not None:
        # preserva a chave (slug) mesmo se o cliente omitir
        chave = (pilar.config or {}).get("chave")
        novo = {**(pilar.config or {}), **patch.config}
        if chave:
            novo["chave"] = chave
        pilar.config = novo
    db.commit()
    db.refresh(pilar)
    return pilar
