"""Endpoints de assets — listar e atualizar status de aprovação."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, Asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/")
def listar_assets(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return db.query(Asset).filter_by(workspace_id=workspace_id).order_by(Asset.criado_em.desc()).limit(100).all()


@router.patch("/{asset_id}/status")
def atualizar_status(asset_id: str, status: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset não encontrado")
    asset.status = status
    db.commit()
    return {"ok": True, "status": status}
