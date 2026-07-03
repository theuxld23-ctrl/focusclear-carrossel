"""Endpoints de workspaces — listar (para o seletor do frontend).

v1 = isolamento no banco, SEM auth (quem acessa o Mac acessa tudo). O seletor do
frontend guarda o workspace escolhido e passa `workspace_id` em toda chamada; o
backend já filtra por workspace em cada endpoint de lista.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db, Workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/")
def listar_workspaces(db: Session = Depends(get_db)):
    return db.query(Workspace).order_by(Workspace.criado_em.asc()).all()
