"""Endpoints de assets — listar, atualizar status e servir o PNG do slide."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, Asset
from config import OUTPUT

router = APIRouter(prefix="/assets", tags=["assets"])

_OUTPUT_ROOT = OUTPUT.resolve()
_MEDIA = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm",
}


@router.get("/")
def listar_assets(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return db.query(Asset).filter_by(workspace_id=workspace_id).order_by(Asset.criado_em.desc()).limit(100).all()


@router.get("/{asset_id}/image")
def servir_imagem(asset_id: str, db: Session = Depends(get_db)):
    """Serve o arquivo do asset (PNG do slide OU vídeo/poster do reel) por FILE PATH.

    Content-Type inferido pela extensão. Só serve arquivos DENTRO de engine/output/
    — barra path traversal. Sem upload externo.
    """
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset or not asset.caminho:
        raise HTTPException(404, "Asset sem arquivo")
    caminho = Path(asset.caminho).resolve()
    if _OUTPUT_ROOT not in caminho.parents:
        raise HTTPException(403, "Caminho fora de engine/output")
    if not caminho.is_file():
        raise HTTPException(404, "Arquivo não encontrado no disco")
    media = _MEDIA.get(caminho.suffix.lower(), "application/octet-stream")
    return FileResponse(caminho, media_type=media)


@router.patch("/{asset_id}/status")
def atualizar_status(asset_id: str, status: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset não encontrado")
    asset.status = status
    db.commit()
    return {"ok": True, "status": status}
