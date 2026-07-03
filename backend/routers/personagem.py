"""Endpoints do personagem (avatar FocusClear) — config no banco + foto de referência.

A foto é salva localmente em engine/assets/ (sem upload externo). O avatar em si
só é gerado na Fase 3; aqui guardamos nome/descrição/tom de voz + a foto de ref.
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db, Personagem
from config import ASSETS

router = APIRouter(prefix="/personagem", tags=["personagem"])

_ASSETS_ROOT = ASSETS.resolve()
_EXT_OK = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _get_ou_cria(db: Session, workspace_id: str) -> Personagem:
    p = db.query(Personagem).filter_by(workspace_id=workspace_id).first()
    if not p:
        p = Personagem(workspace_id=workspace_id, nome="", descricao="", tom_de_voz="")
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@router.get("/")
def obter_personagem(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return _get_ou_cria(db, workspace_id)


class PutPersonagem(BaseModel):
    nome: str = ""
    descricao: str = ""
    tom_de_voz: str = ""


@router.put("/")
def salvar_personagem(
    body: PutPersonagem, workspace_id: str = "focusclear", db: Session = Depends(get_db)
):
    p = _get_ou_cria(db, workspace_id)
    p.nome = body.nome
    p.descricao = body.descricao
    p.tom_de_voz = body.tom_de_voz
    db.commit()
    db.refresh(p)
    return p


@router.post("/foto")
async def upload_foto(
    workspace_id: str = "focusclear",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = _EXT_OK.get(file.content_type or "")
    if not ext:
        raise HTTPException(422, "Envie uma imagem PNG, JPEG ou WEBP")
    destino = _ASSETS_ROOT / f"personagem_{workspace_id}{ext}"
    destino.write_bytes(await file.read())
    # remove variantes de outra extensão (evita foto órfã)
    for e in set(_EXT_OK.values()) - {ext}:
        outra = _ASSETS_ROOT / f"personagem_{workspace_id}{e}"
        if outra.exists():
            outra.unlink()
    p = _get_ou_cria(db, workspace_id)
    p.foto_ref = str(destino)
    db.commit()
    return {"ok": True, "foto_ref": str(destino)}


@router.get("/foto")
def servir_foto(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    p = db.query(Personagem).filter_by(workspace_id=workspace_id).first()
    if not p or not p.foto_ref:
        raise HTTPException(404, "Sem foto de referência")
    caminho = Path(p.foto_ref).resolve()
    if _ASSETS_ROOT not in caminho.parents or not caminho.is_file():
        raise HTTPException(404, "Foto não encontrada")
    return FileResponse(caminho)
